"""Per-thread conversation memory, capped so context doesn't grow forever.

This is short-term memory only — the working context of a live conversation.
Long-term memory is the repo: company/knowledge.md and company/decisions.md.
Anything that matters next month belongs there, not here.

Persisted to disk so a Railway restart mid-conversation doesn't wipe the thread.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path

log = logging.getLogger("marty.memory")

MAX_MESSAGES = 20  # every message is resent on every call in the tool loop
TTL_SECONDS = 60 * 60 * 24 * 3  # threads go cold after three days
SCHEMA = 2  # bump to discard state written by an older, incompatible format


def _plain(value):
    """Convert SDK content blocks into JSON-safe dicts.

    Assistant content comes back from the API as pydantic models. Writing them
    with json.dumps(default=str) stringifies them into reprs, and sending those
    back produces `messages.N.content.0: Input should be an object`. They have
    to be dumped properly or not stored at all.
    """
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def _usable(message) -> bool:
    """A message the API will still accept after a round trip through disk."""
    if not isinstance(message, dict) or "role" not in message:
        return False
    content = message.get("content")
    if isinstance(content, str):
        return True
    if not isinstance(content, list) or not content:
        return False
    # Every block must be an object with a type — a bare string here is the
    # exact shape the API rejects.
    return all(isinstance(b, dict) and "type" in b for b in content)


def _state_path() -> Path:
    """Beside the repo checkout, not inside it — this is scratch, not content."""
    repo_dir = Path(os.environ.get("REPO_DIR", "/data/repo"))
    return repo_dir.parent / "marty-threads.json"


class Threads:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, list[dict]]] = {}
        self._lock = threading.Lock()
        self._path = _state_path()
        self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self._path.read_text())
        except FileNotFoundError:
            return
        except Exception as exc:  # noqa: BLE001 — corrupt state isn't worth crashing over
            log.warning("could not restore conversations: %s", exc)
            return

        if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
            log.info("conversation state is from an older format — starting fresh")
            return

        kept, dropped = {}, 0
        for key, entry in (raw.get("threads") or {}).items():
            messages = [m for m in entry.get("messages", []) if _usable(m)]
            # Never start a thread on a tool_result: its tool_use is gone.
            while messages and _starts_with_tool_result(messages[0]):
                messages = messages[1:]
            if messages:
                kept[key] = (entry["ts"], messages)
            else:
                dropped += 1
        self._store = kept
        log.info("restored %d conversation(s)%s", len(kept),
                 f", dropped {dropped} unusable" if dropped else "")

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "schema": SCHEMA,
                "threads": {k: {"ts": ts, "messages": msgs}
                            for k, (ts, msgs) in self._store.items()},
            }
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload))
            tmp.replace(self._path)  # atomic — a crash mid-write can't corrupt the file
        except Exception as exc:  # noqa: BLE001
            log.warning("could not persist conversations: %s", exc)

    def get(self, key: str) -> list[dict]:
        with self._lock:
            self._expire()
            entry = self._store.get(key)
            return list(entry[1]) if entry else []

    def set(self, key: str, messages: list[dict]) -> None:
        with self._lock:
            self._expire()
            trimmed = [_plain(m) for m in messages[-MAX_MESSAGES:]]
            # Never start a thread on a tool_result — the matching tool_use would
            # be gone and the API rejects it.
            while trimmed and _starts_with_tool_result(trimmed[0]):
                trimmed = trimmed[1:]
            self._store[key] = (time.time(), trimmed)
            self._save()

    def clear(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)
            self._save()

    def _expire(self) -> None:
        cutoff = time.time() - TTL_SECONDS
        for key in [k for k, (ts, _) in self._store.items() if ts < cutoff]:
            del self._store[key]


def _starts_with_tool_result(message: dict) -> bool:
    if message.get("role") != "user":
        return False
    content = message.get("content")
    if not isinstance(content, list) or not content:
        return False
    first = content[0]
    kind = first.get("type") if isinstance(first, dict) else getattr(first, "type", None)
    return kind == "tool_result"

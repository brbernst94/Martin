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

MAX_MESSAGES = 40
TTL_SECONDS = 60 * 60 * 24 * 3  # threads go cold after three days


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
            self._store = {k: (v["ts"], v["messages"]) for k, v in raw.items()}
            log.info("restored %d conversation(s) from %s", len(self._store), self._path)
        except FileNotFoundError:
            pass
        except Exception as exc:  # noqa: BLE001 — corrupt state is not worth crashing over
            log.warning("could not restore conversations: %s", exc)

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {k: {"ts": ts, "messages": msgs} for k, (ts, msgs) in self._store.items()}
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, default=str))
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
            trimmed = messages[-MAX_MESSAGES:]
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

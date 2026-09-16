"""Per-thread conversation memory, capped so context doesn't grow forever."""
from __future__ import annotations

import threading
import time

MAX_MESSAGES = 40
TTL_SECONDS = 60 * 60 * 24 * 3  # threads go cold after three days


class Threads:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, list[dict]]] = {}
        self._lock = threading.Lock()

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

    def clear(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

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

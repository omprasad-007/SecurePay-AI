from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self, ttl_seconds: int = 60, max_items: int = 1024):
        self._ttl = ttl_seconds
        self._max_items = max_items
        self._lock = threading.Lock()
        self._store: dict[str, CacheEntry] = {}

    def get(self, key: str):
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            if entry.expires_at <= now:
                self._store.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: Any) -> None:
        now = time.time()
        with self._lock:
            if len(self._store) >= self._max_items:
                expired = [k for k, entry in self._store.items() if entry.expires_at <= now]
                for item in expired:
                    self._store.pop(item, None)
                if len(self._store) >= self._max_items:
                    oldest_key = next(iter(self._store.keys()))
                    self._store.pop(oldest_key, None)
            self._store[key] = CacheEntry(value=value, expires_at=now + self._ttl)


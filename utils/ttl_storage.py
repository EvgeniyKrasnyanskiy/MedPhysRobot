# utils/ttl_storage.py
#
# TTLMemoryStorage — aiogram 3.x FSM storage with automatic TTL-based eviction.
# Designed for low-RAM environments where abandoned dialogs must not leak memory.
# Drop-in replacement for MemoryStorage(); no external dependencies required.

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey

logger = logging.getLogger("bot")

# Type alias for internal records
_Record = Dict[str, Any]


class TTLMemoryStorage(BaseStorage):
    """
    In-process FSM storage with per-key TTL expiration.

    Each time a state or data is written the last-access timestamp is updated.
    A lightweight background task runs every ``eviction_interval`` seconds and
    removes any keys that have been idle longer than ``ttl`` seconds.

    Args:
        ttl: Seconds of inactivity before a key is evicted. Default: 3600 (1 h).
        eviction_interval: How often the eviction sweep runs, in seconds.
                           Default: 300 (5 min). Keep >= 60 for low-CPU impact.
    """

    def __init__(self, ttl: int = 3600, eviction_interval: int = 300) -> None:
        self._ttl = ttl
        self._eviction_interval = eviction_interval

        # {StorageKey: {"state": str|None, "data": dict, "ts": float}}
        self._storage: Dict[StorageKey, _Record] = {}
        self._lock = asyncio.Lock()
        self._eviction_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Public API — called by aiogram Dispatcher internals
    # ------------------------------------------------------------------

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        async with self._lock:
            record = self._storage.setdefault(key, {"state": None, "data": {}, "ts": 0.0})
            record["state"] = state.state if hasattr(state, "state") else state
            record["ts"] = time.monotonic()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        async with self._lock:
            record = self._storage.get(key)
            if record is None:
                return None
            record["ts"] = time.monotonic()  # refresh on read
            return record["state"]

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        async with self._lock:
            record = self._storage.setdefault(key, {"state": None, "data": {}, "ts": 0.0})
            record["data"] = data
            record["ts"] = time.monotonic()

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        async with self._lock:
            record = self._storage.get(key)
            if record is None:
                return {}
            record["ts"] = time.monotonic()  # refresh on read
            return dict(record["data"])

    async def close(self) -> None:
        """Cancel the background eviction task and clear all stored data."""
        await self._cancel_eviction_task()
        async with self._lock:
            self._storage.clear()
        logger.debug("[TTLStorage] Хранилище закрыто, все состояния очищены")

    # ------------------------------------------------------------------
    # Background eviction
    # ------------------------------------------------------------------

    def start_eviction(self) -> None:
        """
        Launch the background eviction coroutine.
        Safe to call multiple times — only one task will run at a time.
        """
        if self._eviction_task is None or self._eviction_task.done():
            self._eviction_task = asyncio.create_task(
                self._eviction_loop(), name="ttl_storage_eviction"
            )
            logger.debug(
                "[TTLStorage] Фоновая эвикция запущена (TTL=%ds, интервал=%ds)",
                self._ttl,
                self._eviction_interval,
            )

    async def _cancel_eviction_task(self) -> None:
        if self._eviction_task and not self._eviction_task.done():
            self._eviction_task.cancel()
            try:
                await self._eviction_task
            except asyncio.CancelledError:
                pass
            self._eviction_task = None

    async def _eviction_loop(self) -> None:
        """Periodically sweep storage and remove expired keys."""
        while True:
            await asyncio.sleep(self._eviction_interval)
            await self._evict_expired()

    async def _evict_expired(self) -> None:
        """Remove keys whose last-access timestamp exceeds TTL."""
        now = time.monotonic()
        async with self._lock:
            expired = [k for k, v in self._storage.items() if now - v["ts"] > self._ttl]
            for key in expired:
                del self._storage[key]

        if expired:
            logger.info(
                "[TTLStorage] Эвикция: удалено %d устаревших FSM-состояний (TTL=%ds)",
                len(expired),
                self._ttl,
            )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Current number of stored keys (approximate, no lock)."""
        return len(self._storage)

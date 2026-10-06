# middlewares/album.py

import asyncio
import time
from typing import Callable, Awaitable, Dict, Any, List
from aiogram import BaseMiddleware
from aiogram.types import Message


class AlbumMiddleware(BaseMiddleware):
    def __init__(self, wait_time: float = 0.5, max_wait: float = 3.0):
        self.wait_time = wait_time
        self.max_wait = max_wait
        self.albums: Dict[str, List[Message]] = {}
        self.recent_groups: Dict[str, float] = {}
        self.lock = asyncio.Lock()

    def _cleanup_recent(self, now: float) -> None:
        """Evicts group keys older than 30 seconds to prevent memory leaks."""
        expired = [k for k, ts in self.recent_groups.items() if now - ts > 30.0]
        for k in expired:
            del self.recent_groups[k]

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if not event.media_group_id:
            return await handler(event, data)

        group_key = f"{event.chat.id}:{event.media_group_id}"
        now = time.monotonic()

        async with self.lock:
            self._cleanup_recent(now)
            if group_key in self.recent_groups:
                # Group already processed and dispatched; ignore stragglers
                return None

            album = self.albums.setdefault(group_key, [])
            album.append(event)

            if len(album) > 1:
                # Only the first event in the group manages the debounce timer
                return None

        # Collector coroutine (first message in group)
        start_time = time.monotonic()
        prev_count = 1

        while True:
            await asyncio.sleep(self.wait_time)
            async with self.lock:
                current_count = len(self.albums.get(group_key, []))
                elapsed = time.monotonic() - start_time

                # Stop waiting if no new messages arrived or max_wait exceeded
                if current_count == prev_count or elapsed >= self.max_wait:
                    collected = self.albums.pop(group_key, [])
                    self.recent_groups[group_key] = time.monotonic()
                    data["album"] = collected
                    break

                prev_count = current_count

        return await handler(event, data)


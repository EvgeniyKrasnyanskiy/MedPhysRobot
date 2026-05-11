# middlewares/album.py

from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Awaitable, Dict, Any, List
import asyncio

class AlbumMiddleware(BaseMiddleware):
    def __init__(self, wait_time: float = 0.3):
        self.wait_time = wait_time
        self.albums: Dict[str, List[Message]] = {}
        self.lock = asyncio.Lock()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if not event.media_group_id:
            return await handler(event, data)

        group_key = f"{event.chat.id}:{event.media_group_id}"
        
        async with self.lock:
            album = self.albums.setdefault(group_key, [])
            album.append(event)

        await asyncio.sleep(self.wait_time)

        async with self.lock:
            if group_key in self.albums and self.albums[group_key][0] == event:
                data["album"] = self.albums[group_key].copy()
                del self.albums[group_key]
                return await handler(event, data)
        return None

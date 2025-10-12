# middlewares/album.py

from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Awaitable, Dict, Any, List
import asyncio

class AlbumMiddleware(BaseMiddleware):
    def __init__(self, wait_time: float = 0.3):
        self.wait_time = wait_time
        self.albums: Dict[str, List[Message]] = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if not event.media_group_id:
            return await handler(event, data)

        group_key = f"{event.chat.id}:{event.media_group_id}"
        album = self.albums.setdefault(group_key, [])
        album.append(event)

        await asyncio.sleep(self.wait_time)

        if album and album[0] == event:
            data["album"] = album.copy()
            del self.albums[group_key]
            return await handler(event, data)

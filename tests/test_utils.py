import pytest
from aiogram.types import MessageEntity
from utils.sender import utf16_len, shift_entities

def test_utf16_len():
    # Regular text
    assert utf16_len("hello") == 5
    # Emoji (usually 2 units in UTF-16)
    assert utf16_len("📨") == 2
    # Combined
    assert utf16_len("📨 hello") == 2 + 1 + 5 # emoji + space + hello

def test_shift_entities():
    original_entities = [
        MessageEntity(type="bold", offset=0, length=5),
        MessageEntity(type="text_link", offset=6, length=5, url="https://example.com")
    ]
    
    # Shift by 10
    shifted = shift_entities(original_entities, 10)
    
    assert len(shifted) == 2
    assert shifted[0].offset == 10
    assert shifted[0].length == 5
    assert shifted[1].offset == 16
    assert shifted[1].length == 5
    assert shifted[1].url == "https://example.com"

def test_shift_entities_none():
    assert shift_entities(None, 10) == []
    assert shift_entities([], 10) == []

def test_shift_entities_zero_offset():
    original = [MessageEntity(type="bold", offset=0, length=5)]
    shifted = shift_entities(original, 0)
    assert shifted == original


@pytest.mark.asyncio
async def test_album_middleware():
    from middlewares.album import AlbumMiddleware
    from unittest.mock import MagicMock, AsyncMock
    from aiogram.types import Message, Chat
    import asyncio

    middleware = AlbumMiddleware(wait_time=0.05, max_wait=0.5)
    handler = AsyncMock(return_value="handled")

    chat = Chat(id=100, type="private")
    msg1 = MagicMock(spec=Message, chat=chat, media_group_id="group_1", message_id=1)
    msg2 = MagicMock(spec=Message, chat=chat, media_group_id="group_1", message_id=2)

    task1 = asyncio.create_task(middleware(handler, msg1, {}))
    await asyncio.sleep(0.01)
    task2 = asyncio.create_task(middleware(handler, msg2, {}))

    res1, res2 = await asyncio.gather(task1, task2)

    assert res1 == "handled"
    assert res2 is None
    handler.assert_called_once()
    _, call_data = handler.call_args[0]
    assert len(call_data["album"]) == 2
    assert call_data["album"][0] == msg1
    assert call_data["album"][1] == msg2

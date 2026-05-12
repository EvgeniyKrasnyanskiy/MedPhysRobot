import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram import Bot
from aiogram.types import Message, Chat
from utils.sender import send_content_to_group

@pytest.mark.asyncio
async def test_send_content_to_group_html():
    bot = AsyncMock(spec=Bot)
    chat = Chat(id=1, type="private")
    
    # Simulate a message with hidden link in HTML
    html_content = "Hello <a href=\"https://world.com\">world</a>"
    
    message = MagicMock(spec=Message)
    message.html_text = html_content
    message.text = "Hello world"
    message.caption = None
    message.chat = chat
    message.message_id = 123
    # Media types
    message.photo = None
    message.video = None
    message.document = None
    message.audio = None
    message.voice = None
    message.animation = None
    message.sticker = None
    message.video_note = None
    message.poll = None
    message.media_group_id = None
    
    prefix_html = "<b>HEADER</b> "
    
    await send_content_to_group(
        message=message,
        bot=bot,
        chat_id=999,
        prefix=prefix_html,
        parse_mode="HTML"
    )
    
    bot.send_message.assert_called_once()
    args, kwargs = bot.send_message.call_args
    
    assert kwargs["text"] == "<b>HEADER</b> Hello <a href=\"https://world.com\">world</a>"
    assert kwargs["parse_mode"] == "HTML"

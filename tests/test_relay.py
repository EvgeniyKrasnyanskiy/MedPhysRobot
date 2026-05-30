import pytest
import html
from aiogram.types import User, Message
from handlers.relay import format_header

def test_format_header_basic():
    user = User(id=123, is_bot=False, first_name="Ivan", username="ivan_test")
    html_text = format_header(user)
    
    assert "Ivan" in html_text
    assert "@ivan_test" in html_text
    assert "123" in html_text
    assert "<b>" in html_text
    assert "tg://user?id=123" in html_text
    assert "<code>" in html_text

def test_format_header_no_username():
    user = User(id=456, is_bot=False, first_name="NoName")
    html_text = format_header(user)
    
    assert "NoName" in html_text
    assert "@" not in html_text
    assert "456" in html_text

def test_album_caption_logic():
    user = User(id=1, is_bot=False, first_name="User")
    header_html = format_header(user)
    
    user_html = "<i>Photo 1</i>"
    caption = header_html + user_html
    
    assert caption.startswith("📨")
    assert "<i>Photo 1</i>" in caption
    assert "<b>" in caption


@pytest.mark.asyncio
async def test_handle_group_reply_ignored_when_not_bot_reply():
    from handlers.relay import handle_group_reply
    from unittest.mock import AsyncMock, MagicMock
    from aiogram import Bot
    
    bot = AsyncMock(spec=Bot)
    bot.id = 99999
    
    # Сообщение, на которое отвечают (отправлено другим админом, не ботом)
    reply_to_message = MagicMock(spec=Message)
    reply_to_message.message_id = 555
    reply_to_message.from_user = User(id=11111, is_bot=False, first_name="OtherAdmin")
    
    # Наш ответ
    message = MagicMock(spec=Message)
    message.reply_to_message = reply_to_message
    message.reply = AsyncMock()
    
    await handle_group_reply(message=message, bot=bot)
    message.reply.assert_not_called()


@pytest.mark.asyncio
async def test_handle_admin_edit_ignored_when_not_bot_reply():
    from handlers.relay import handle_admin_edit
    from unittest.mock import AsyncMock, MagicMock
    from aiogram import Bot
    
    bot = AsyncMock(spec=Bot)
    bot.id = 99999
    
    # 1. Сообщение, не являющееся ответом вообще
    message_no_reply = MagicMock(spec=Message)
    message_no_reply.reply_to_message = None
    message_no_reply.reply = AsyncMock()
    
    await handle_admin_edit(message=message_no_reply, bot=bot)
    message_no_reply.reply.assert_not_called()
    
    # 2. Сообщение, являющееся ответом на сообщение другого админа (не бота)
    reply_to_message = MagicMock(spec=Message)
    reply_to_message.from_user = User(id=11111, is_bot=False, first_name="OtherAdmin")
    
    message_admin_reply = MagicMock(spec=Message)
    message_admin_reply.reply_to_message = reply_to_message
    message_admin_reply.reply = AsyncMock()
    
    await handle_admin_edit(message=message_admin_reply, bot=bot)
    message_admin_reply.reply.assert_not_called()


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


def test_partition_media_album():
    from handlers.relay import partition_media_album
    from aiogram.types import Document, PhotoSize, Audio
    from unittest.mock import MagicMock

    def mock_msg(doc=False, photo=False, audio=False):
        m = MagicMock(spec=Message)
        m.document = MagicMock(spec=Document) if doc else None
        m.photo = [MagicMock(spec=PhotoSize)] if photo else None
        m.video = None
        m.audio = MagicMock(spec=Audio) if audio else None
        return m

    # 3 documents
    album_docs = [mock_msg(doc=True) for _ in range(3)]
    groups = partition_media_album(album_docs)
    assert len(groups) == 1
    assert len(groups[0]) == 3

    # 2 photos and 2 docs (mixed) -> separated into 2 groups
    mixed_album = [mock_msg(photo=True), mock_msg(photo=True), mock_msg(doc=True), mock_msg(doc=True)]
    groups = partition_media_album(mixed_album)
    assert len(groups) == 2
    assert len(groups[0]) == 2
    assert len(groups[1]) == 2


@pytest.mark.asyncio
async def test_handle_private_message_document_album(monkeypatch):
    from handlers.relay import handle_private_message
    from unittest.mock import AsyncMock, MagicMock
    from aiogram.types import Document, InputMediaDocument

    # Mock DB functions
    saved_mappings = []
    monkeypatch.setattr("handlers.relay.is_banned", lambda uid: False)
    monkeypatch.setattr("handlers.relay.is_muted", lambda uid: False)
    monkeypatch.setattr("handlers.relay.save_mapping", lambda fwd_id, uid, orig_id: saved_mappings.append((fwd_id, uid, orig_id)))

    user = User(id=777, is_bot=False, first_name="DocSender")
    bot = AsyncMock()

    # Simulate 2 sent messages returned by bot.send_media_group
    sent_msg1 = MagicMock(spec=Message, message_id=1001)
    sent_msg2 = MagicMock(spec=Message, message_id=1002)
    bot.send_media_group = AsyncMock(return_value=[sent_msg1, sent_msg2])

    doc1 = MagicMock(spec=Document, file_id="doc_fid_1")
    doc2 = MagicMock(spec=Document, file_id="doc_fid_2")

    msg1 = MagicMock(spec=Message, message_id=501, from_user=user, photo=None, video=None, audio=None, document=doc1, html_text="Report 1")
    msg1.answer = AsyncMock()
    msg2 = MagicMock(spec=Message, message_id=502, from_user=user, photo=None, video=None, audio=None, document=doc2, html_text="Report 2")
    msg2.answer = AsyncMock()

    album = [msg1, msg2]

    await handle_private_message(message=msg1, bot=bot, album=album)

    # Verify send_media_group was called with InputMediaDocument
    bot.send_media_group.assert_called_once()
    call_args = bot.send_media_group.call_args[1]
    media_list = call_args["media"]
    assert len(media_list) == 2
    assert isinstance(media_list[0], InputMediaDocument)
    assert isinstance(media_list[1], InputMediaDocument)
    assert media_list[0].media == "doc_fid_1"
    assert media_list[1].media == "doc_fid_2"

    # Verify mappings saved for BOTH files
    assert len(saved_mappings) == 2
    assert saved_mappings[0] == (1001, 777, 501)
    assert saved_mappings[1] == (1002, 777, 502)

    msg1.answer.assert_called_once_with("✅ Ваше сообщение получено!")


@pytest.mark.asyncio
async def test_handle_private_message_album_long_caption(monkeypatch):
    from handlers.relay import handle_private_message
    from unittest.mock import AsyncMock, MagicMock
    from aiogram.types import Document

    monkeypatch.setattr("handlers.relay.is_banned", lambda uid: False)
    monkeypatch.setattr("handlers.relay.is_muted", lambda uid: False)
    monkeypatch.setattr("handlers.relay.save_mapping", lambda *args: None)

    user = User(id=888, is_bot=False, first_name="LongDescUser")
    bot = AsyncMock()

    sent_msg1 = MagicMock(spec=Message, message_id=2001)
    sent_msg2 = MagicMock(spec=Message, message_id=2002)
    bot.send_media_group = AsyncMock(return_value=[sent_msg1, sent_msg2])
    bot.send_message = AsyncMock()

    doc1 = MagicMock(spec=Document, file_id="doc_fid_1")
    doc2 = MagicMock(spec=Document, file_id="doc_fid_2")

    # Caption that exceeds 1024 chars
    long_text = "A" * 1050
    msg1 = MagicMock(spec=Message, message_id=601, from_user=user, photo=None, video=None, audio=None, document=doc1, html_text=long_text)
    msg1.answer = AsyncMock()
    msg2 = MagicMock(spec=Message, message_id=602, from_user=user, photo=None, video=None, audio=None, document=doc2, html_text="")

    await handle_private_message(message=msg1, bot=bot, album=[msg1, msg2])

    # Header was sent separately as send_message
    bot.send_message.assert_called()
    bot.send_media_group.assert_called_once()


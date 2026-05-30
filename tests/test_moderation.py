import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock
from aiogram import Bot
from aiogram.types import Message, User, PhotoSize
from aiogram.exceptions import TelegramBadRequest
from handlers.moderation import (
    parse_mute_duration,
    extract_message_id_from_link,
    make_channel_post_link,
    send_to_channel
)

def test_parse_mute_duration_default():
    assert parse_mute_duration("/mute") == timedelta(hours=2)
    assert parse_mute_duration("/mute   ") == timedelta(hours=2)
    assert parse_mute_duration("/mute ") == timedelta(hours=2)

def test_parse_mute_duration_valid():
    assert parse_mute_duration("/mute 30m") == timedelta(minutes=30)
    assert parse_mute_duration("/mute 2h") == timedelta(hours=2)
    assert parse_mute_duration("/mute 5") == timedelta(hours=5)
    assert parse_mute_duration("/mute 3d") == timedelta(days=3)
    assert parse_mute_duration("/mute 1w") == timedelta(weeks=1)

def test_parse_mute_duration_invalid():
    assert parse_mute_duration("/mute abc") is None
    assert parse_mute_duration("/mute -5") is None
    assert parse_mute_duration("/mute 5x") is None


def test_extract_message_id_from_link():
    # Просто число
    assert extract_message_id_from_link("12345") == 12345
    assert extract_message_id_from_link("  67890  ") == 67890
    
    # Публичная ссылка
    assert extract_message_id_from_link("https://t.me/MedPhysProChannel/123") == 123
    assert extract_message_id_from_link("t.me/MedPhysProChannel/456") == 456
    
    # Приватная ссылка
    assert extract_message_id_from_link("https://t.me/c/1234567890/789") == 789
    assert extract_message_id_from_link("https://t.me/c/987654321/111?thread=222") == 111
    
    # Невалидные варианты
    assert extract_message_id_from_link("https://t.me/MedPhysProChannel") is None
    assert extract_message_id_from_link("abc") is None
    assert extract_message_id_from_link("") is None


def test_make_channel_post_link():
    # С юзернеймом
    assert make_channel_post_link(-10012345, 999, "MedPhysProChannel") == "https://t.me/MedPhysProChannel/999"
    assert make_channel_post_link(-10012345, 999, "@MedPhysProChannel") == "https://t.me/MedPhysProChannel/999"
    
    # Без юзернейма (приватный)
    assert make_channel_post_link(-100123456789, 777) == "https://t.me/c/123456789/777"
    assert make_channel_post_link(-123456789, 777) == "https://t.me/c/123456789/777"


@pytest.mark.asyncio
async def test_send_to_channel_edit_text_success():
    bot = AsyncMock(spec=Bot)
    
    # Сообщение-ответ (текстовое)
    reply_message = MagicMock(spec=Message)
    reply_message.photo = None
    reply_message.video = None
    reply_message.document = None
    reply_message.audio = None
    reply_message.animation = None
    reply_message.html_text = "<b>New Text</b>"
    reply_message.message_id = 100
    
    # Наша команда /send_to_channel 456
    message = MagicMock(spec=Message)
    message.reply_to_message = reply_message
    message.bot = bot
    message.from_user = User(id=123, is_bot=False, first_name="Admin", full_name="Super Admin")
    message.reply = AsyncMock()
    
    # Вызываем редактирование
    await send_to_channel(message, "456")
    
    # Проверяем, что вызвана правильная функция API
    bot.edit_message_text.assert_called_once()
    kwargs = bot.edit_message_text.call_args[1]
    assert kwargs["message_id"] == 456
    assert kwargs["text"] == "<b>New Text</b>"
    assert kwargs["parse_mode"] == "HTML"
    
    # Проверяем отправку лога
    bot.send_message.assert_called_once()
    
    # Проверяем ответ администратору
    message.reply.assert_called_once_with("✅ Сообщение в канале успешно отредактировано")


@pytest.mark.asyncio
async def test_send_to_channel_edit_caption_success():
    bot = AsyncMock(spec=Bot)
    
    # Сообщение-ответ (с фото)
    reply_message = MagicMock(spec=Message)
    reply_message.photo = [MagicMock(spec=PhotoSize)]
    reply_message.video = None
    reply_message.document = None
    reply_message.audio = None
    reply_message.animation = None
    reply_message.html_text = "<i>New Caption</i>"
    reply_message.message_id = 100
    
    # Наша команда /send_to_channel https://t.me/c/123/789
    message = MagicMock(spec=Message)
    message.reply_to_message = reply_message
    message.bot = bot
    message.from_user = User(id=123, is_bot=False, first_name="Admin", full_name="Super Admin")
    message.reply = AsyncMock()
    
    # Вызываем редактирование
    await send_to_channel(message, "https://t.me/c/123/789")
    
    # Проверяем, что вызвана правильная функция API для медиа (caption)
    bot.edit_message_caption.assert_called_once()
    kwargs = bot.edit_message_caption.call_args[1]
    assert kwargs["message_id"] == 789
    assert kwargs["caption"] == "<i>New Caption</i>"
    assert kwargs["parse_mode"] == "HTML"
    
    # Проверяем лог и ответ
    bot.send_message.assert_called_once()
    message.reply.assert_called_once_with("✅ Сообщение в канале успешно отредактировано")


@pytest.mark.asyncio
async def test_send_to_channel_edit_error():
    bot = AsyncMock(spec=Bot)
    # Симулируем ошибку при вызове edit_message_text
    bot.edit_message_text.side_effect = TelegramBadRequest(
        message="Bad Request: message can't be edited",
        method=MagicMock()
    )
    
    reply_message = MagicMock(spec=Message)
    reply_message.photo = None
    reply_message.video = None
    reply_message.document = None
    reply_message.audio = None
    reply_message.animation = None
    reply_message.html_text = "<b>Some Text</b>"
    
    message = MagicMock(spec=Message)
    message.reply_to_message = reply_message
    message.bot = bot
    message.from_user = User(id=123, is_bot=False, first_name="Admin", full_name="Super Admin")
    message.reply = AsyncMock()
    
    await send_to_channel(message, "999")
    
    # Проверяем, что бот ответил сообщением об ошибке
    message.reply.assert_called_once()
    error_reply = message.reply.call_args[0][0]
    assert "❌ Не удалось отредактировать сообщение в канале" in error_reply

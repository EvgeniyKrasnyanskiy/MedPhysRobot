import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User
from handlers.thanks import detect_thanks

@pytest.mark.asyncio
async def test_detect_thanks_valid():
    # Симулируем корректную благодарность
    reply_user = User(id=456, is_bot=False, first_name="John", last_name="Doe")
    sender_user = User(id=123, is_bot=False, first_name="Alice", last_name="Smith")
    
    reply_message = MagicMock(spec=Message)
    reply_message.from_user = reply_user
    
    message = MagicMock(spec=Message)
    message.text = "Спасибо большое за помощь!"
    message.from_user = sender_user
    message.reply_to_message = reply_message
    
    # Мокаем инкремент
    with patch("handlers.thanks.increment_thanks") as mock_increment:
        await detect_thanks(message)
        mock_increment.assert_called_once_with(456, "John Doe")


@pytest.mark.asyncio
async def test_detect_thanks_self_thank():
    # Благодарность самому себе (не должна начисляться)
    user = User(id=123, is_bot=False, first_name="Self", last_name="User")
    
    reply_message = MagicMock(spec=Message)
    reply_message.from_user = user
    
    message = MagicMock(spec=Message)
    message.text = "спасибо"
    message.from_user = user
    message.reply_to_message = reply_message
    
    with patch("handlers.thanks.increment_thanks") as mock_increment:
        await detect_thanks(message)
        mock_increment.assert_not_called()


@pytest.mark.asyncio
async def test_detect_thanks_bot_thank():
    # Благодарность боту (не должна начисляться)
    reply_user = User(id=456, is_bot=True, first_name="MyBot")
    sender_user = User(id=123, is_bot=False, first_name="Alice")
    
    reply_message = MagicMock(spec=Message)
    reply_message.from_user = reply_user
    
    message = MagicMock(spec=Message)
    message.text = "Спасибо, бот!"
    message.from_user = sender_user
    message.reply_to_message = reply_message
    
    with patch("handlers.thanks.increment_thanks") as mock_increment:
        await detect_thanks(message)
        mock_increment.assert_not_called()

# handlers/start.py

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from utils.logger import get_logger

logger = get_logger("start")
router = Router()

@router.message(CommandStart())
async def handle_start(message: Message):
    await message.answer(
        """👋 Теперь отправьте ваше сообщение.
Бот перешлёт его всем администраторам.

⚠️ Внимание!
Telegram работает нестабильно.
Если вам не ответили, пожалуйста,
попытайтесь отправить сообщение позже."""
    )
    logger.info(f"[START] Обрабатываю /start от {message.from_user.id}")

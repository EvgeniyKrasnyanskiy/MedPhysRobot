# handlers/start.py

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from utils.logger import setup_logger

logger = setup_logger("start")
router = Router()

@router.message(CommandStart())
async def handle_start(message: Message):
    await message.answer("👋 Теперь отправьте ваше сообщение. \nБот перешлёт его всем админам.")
    logger.info(f"[START] Обрабатываю /start от {message.from_user.id}")

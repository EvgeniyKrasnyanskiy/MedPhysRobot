# handlers/status.py

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from utils.db import get_user_status
from utils.config import RELAY_GROUP_ID
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger("status")
router = Router()

@router.message(F.chat.id == RELAY_GROUP_ID, Command("/status"))
async def cmd_status(message: Message):
    user_id = message.from_user.id
    logger.info(f"[STATUS] Запрос статуса от пользователя {user_id}")

    status = get_user_status(user_id)

    if status["banned"]:
        await message.answer("🚫 Вы заблокированы и не можете отправлять сообщения.")
        return

    if status["muted"]:
        until = datetime.fromisoformat(status["muted_until"]).strftime("%d.%m.%Y %H:%M")
        await message.answer(f"🔇 Вы временно замьючены до {until} (UTC).")
        return

    await message.answer("✅ У вас нет ограничений. Вы можете отправлять сообщения.")

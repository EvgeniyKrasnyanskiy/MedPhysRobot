# handlers/relay.py

from aiogram import Router, F
from aiogram.types import Message
from utils.config import RELAY_GROUP_ID
from utils.db import save_mapping
from utils.logger import setup_logger
import re
from utils.db import (
    save_mapping,
    user_exists,
    mark_user_sent,
    get_user_by_forwarded,
    is_banned,
    is_muted
)
from utils.db import is_banned, is_muted
from aiogram.filters import CommandStart
from aiogram.filters import Command


router = Router()
logger = setup_logger("relay")

@router.message(
    F.chat.type == "private",
    F.text,
    ~F.text.startswith("/")
)
async def handle_private_message(message: Message):
    user_id = message.from_user.id
    logger.info(f"[RELAY] Обрабатываю сообщение: {message.text}")

    if is_banned(user_id):
        await message.answer("🚫 Вы заблокированы и не можете отправлять сообщения.")
        return

    if is_muted(user_id):
        await message.answer("🔇 Вы временно замьючены. Попробуйте позже.")
        return

    forwarded = await message.forward(chat_id=RELAY_GROUP_ID)
    logger.info(f"[RELAY] forwarded.message_id = {forwarded.message_id}")
    save_mapping(forwarded.message_id, user_id, message.message_id)
    logger.info(f"[RELAY] Сообщение от {user_id} переслано в группу {RELAY_GROUP_ID}")

    await message.answer("✅ Ваше сообщение получено!")


@router.message(F.chat.id == RELAY_GROUP_ID, F.reply_to_message)
async def handle_group_reply(message: Message):
    logger.info("[RELAY] Обработчик ответа сработал")

    forwarded_id = message.reply_to_message.message_id
    user_id = get_user_by_forwarded(forwarded_id)
    logger.info(f"[RELAY] reply_to_message_id = {forwarded_id}")
    logger.info(f"[RELAY] Найден user_id из базы: {user_id}")

    if user_id:
        try:
            await message.send_copy(chat_id=user_id)
            logger.info(f"[RELAY] Ответ переслан пользователю {user_id}")
        except Exception as e:
            logger.error(f"[RELAY] Ошибка пересылки ответа: {e}")
    else:
        logger.warning(f"[RELAY] Не удалось найти user_id для forwarded_id={forwarded_id}")

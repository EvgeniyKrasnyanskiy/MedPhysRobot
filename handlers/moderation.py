# handlers/moderation.py

from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from utils.db import (
    mute_user,
    unmute_user,
    ban_user,
    unban_user,
    get_user_by_forwarded,
    get_user_status
)
from utils.config import RELAY_GROUP_ID
from utils.logger import setup_logger
from datetime import datetime, timedelta
import asyncio

router = Router()
logger = setup_logger("moderation")
logger.info("[MOD] moderation.py загружен")


def extract_user_id_from_reply(message: Message) -> int | None:
    if not message.reply_to_message:
        return None

    # Пробуем получить ID через карту пересылки
    mapped_id = get_user_by_forwarded(message.reply_to_message.message_id)
    if mapped_id:
        return mapped_id

    # Если пересылка не найдена — fallback на from_user.id
    return message.reply_to_message.from_user.id


async def reply_required(message: Message, command: str):
    info = await message.reply(f"❗ Используйте {command} в ответ на сообщение.")
    await asyncio.sleep(3)
    try:
        await message.delete()
        await info.delete()
    except Exception as e:
        logger.warning(f"[MOD] Не удалось удалить сообщения: {e}")


# 🔇 /mute
@router.message(F.text.startswith("/mute"))
async def cmd_mute(message: Message, bot: Bot):
    logger.info(f"[MOD] cmd_mute вызван: text={message.text}, chat_id={message.chat.id}")
    if message.chat.id != RELAY_GROUP_ID:
        return

    if not message.reply_to_message:
        await reply_required(message, "/mute")
        return

    user_id = extract_user_id_from_reply(message)
    logger.info(f"[MOD] user_id из reply: {user_id}")
    if not user_id:
        await reply_required(message, "/mute")
        return

    muted_until = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    mute_user(user_id, muted_until=muted_until)

    logger.info(f"[MOD] Замьючен user_id={user_id} до {muted_until} UTC")
    await message.reply(f"🔇 Пользователь {user_id} замьючен до {muted_until} UTC.")

    try:
        await bot.send_message(user_id, f"🔇 Вы были временно замьючены до {muted_until} UTC.")
    except Exception as e:
        logger.warning(f"[MOD] Не удалось отправить уведомление user_id={user_id}: {e}")


# 🔊 /unmute
@router.message(F.text.startswith("/unmute"))
async def cmd_unmute(message: Message, bot: Bot):
    logger.info(f"[MOD] cmd_unmute вызван: text={message.text}, chat_id={message.chat.id}")
    if message.chat.id != RELAY_GROUP_ID:
        return

    if not message.reply_to_message:
        await reply_required(message, "/unmute")
        return

    user_id = extract_user_id_from_reply(message)
    logger.info(f"[MOD] user_id из reply: {user_id}")
    if not user_id:
        await reply_required(message, "/unmute")
        return

    unmute_user(user_id)
    logger.info(f"[MOD] Размьючен user_id={user_id}")
    await message.reply(f"🔊 Пользователь {user_id} размьючен.")

    try:
        await bot.send_message(user_id, "🔊 Вы были размьючены.")
    except Exception as e:
        logger.warning(f"[MOD] Не удалось отправить уведомление user_id={user_id}: {e}")


# 🚫 /ban
@router.message(F.text.startswith("/ban"))
async def cmd_ban(message: Message, bot: Bot):
    logger.info(f"[MOD] cmd_ban вызван: text={message.text}, chat_id={message.chat.id}")
    if message.chat.id != RELAY_GROUP_ID:
        return

    if not message.reply_to_message:
        await reply_required(message, "/ban")
        return

    user_id = extract_user_id_from_reply(message)
    logger.info(f"[MOD] user_id из reply: {user_id}")
    if not user_id:
        await reply_required(message, "/ban")
        return

    banned_at = datetime.utcnow().isoformat()
    ban_user(user_id, banned_at=banned_at)

    logger.info(f"[MOD] Забанен user_id={user_id} в {banned_at} UTC")
    await message.reply(f"🚫 Пользователь {user_id} заблокирован в {banned_at} UTC.")

    try:
        await bot.send_message(user_id, f"🚫 Вы были заблокированы в {banned_at} UTC.")
    except Exception as e:
        logger.warning(f"[MOD] Не удалось отправить уведомление user_id={user_id}: {e}")


# ✅ /unban
@router.message(F.text.startswith("/unban"))
async def cmd_unban(message: Message, bot: Bot):
    logger.info(f"[MOD] cmd_unban вызван: text={message.text}, chat_id={message.chat.id}")
    if message.chat.id != RELAY_GROUP_ID:
        return

    if not message.reply_to_message:
        await reply_required(message, "/unban")
        return

    user_id = extract_user_id_from_reply(message)
    logger.info(f"[MOD] user_id из reply: {user_id}")
    if not user_id:
        await reply_required(message, "/unban")
        return

    unban_user(user_id)
    logger.info(f"[MOD] Разбанен user_id={user_id}")
    await message.reply(f"✅ Пользователь {user_id} разблокирован.")

    try:
        await bot.send_message(user_id, "✅ Вы были разблокированы.")
    except Exception as e:
        logger.warning(f"[MOD] Не удалось отправить уведомление user_id={user_id}: {e}")


# ❓ /status
@router.message(Command("status"))
async def cmd_status(message: Message):
    user_id = extract_user_id_from_reply(message)
    if not user_id:
        await reply_required(message, "/status")
        return

    logger.info(f"[STATUS] Запрос статуса для user_id={user_id}")

    try:
        status = get_user_status(user_id)
    except Exception as e:
        logger.error(f"[STATUS] Ошибка при получении статуса: {e}")
        await message.answer("⚠️ Не удалось получить статус. Попробуйте позже.")
        return

    if not status:
        await message.answer("⚠️ Статус не найден.")
        return

    if status.get("banned"):
        banned_at = status.get("banned_at")
        await message.answer(f"🚫 Пользователь {user_id} заблокирован с {banned_at} UTC.")
        return

    if status.get("muted"):
        muted_until = status.get("muted_until")
        await message.answer(f"🔇 Пользователь {user_id} замьючен до {muted_until} UTC.")
        return

    await message.answer(f"✅ У пользователя {user_id} нет ограничений.")



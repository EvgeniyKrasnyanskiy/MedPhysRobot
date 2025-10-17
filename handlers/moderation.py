# handlers/moderation.py

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
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
from utils.config import ADMIN_GROUP_ID, MEDPHYSPRO_GROUP_ID, LOG_CHANNEL_ID, MEDPHYSPRO_GROUP_TOPIC_ID
from utils.logger import get_logger
from datetime import datetime, timedelta
import asyncio

from utils.sender import send_content_to_group

router = Router()
logger = get_logger("moderation")
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
@router.message(F.chat.id == ADMIN_GROUP_ID, Command("mute", ignore_mention=True, ignore_case=True))
async def cmd_mute(message: Message, bot: Bot):
    logger.info(f"[MOD] cmd_mute вызван: text={message.text}, chat_id={message.chat.id}")
    if message.chat.id != ADMIN_GROUP_ID:
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
@router.message(F.chat.id == ADMIN_GROUP_ID, Command("unmute", ignore_mention=True, ignore_case=True))
async def cmd_unmute(message: Message, bot: Bot):
    logger.info(f"[MOD] cmd_unmute вызван: text={message.text}, chat_id={message.chat.id}")
    if message.chat.id != ADMIN_GROUP_ID:
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
@router.message(F.chat.id == ADMIN_GROUP_ID, Command("ban", ignore_mention=True, ignore_case=True))
async def cmd_ban(message: Message, bot: Bot):
    logger.info(f"[MOD] cmd_ban вызван: text={message.text}, chat_id={message.chat.id}")
    if message.chat.id != ADMIN_GROUP_ID:
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
@router.message(F.chat.id == ADMIN_GROUP_ID, Command("unban", ignore_mention=True, ignore_case=True))
async def cmd_unban(message: Message, bot: Bot):
    logger.info(f"[MOD] cmd_unban вызван: text={message.text}, chat_id={message.chat.id}")
    if message.chat.id != ADMIN_GROUP_ID:
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
@router.message(F.chat.id == ADMIN_GROUP_ID, Command("status", ignore_mention=True, ignore_case=True))
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

# ↪️/send_to_pro_group
@router.message(Command("send_to_pro_group"), F.chat.id == ADMIN_GROUP_ID, F.reply_to_message)
async def send_to_pro_group(message: Message):
    try:
        thread_id = MEDPHYSPRO_GROUP_TOPIC_ID
        suffix = ""  # Можно добавить подпись, если нужно

        sent = await send_content_to_group(
            message=message.reply_to_message,
            bot=message.bot,
            chat_id=MEDPHYSPRO_GROUP_ID,
            thread_id=thread_id,
            suffix=suffix
        )

        if not sent:
            await message.reply("⚠️ Не удалось определить тип сообщения для пересылки")
            return

        # Лог в файл
        logger.info(
            f"[MOD] Переслано в PRO-группу: from_msg_id={message.reply_to_message.message_id}, "
            f"to_msg_id={sent.message_id}, by={message.from_user.id}"
        )

        # Лог в канал логов
        await message.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=(
                f"📤 <b>Переслано из админской группы в PRO-группу</b>\n"
                f"↪️ Исходное msg_id: <code>{message.reply_to_message.message_id}</code>\n"
                f"📨 Новое msg_id: <code>{sent.message_id}</code>\n"
                f"👤 Отправитель: <a href=\"tg://user?id={message.from_user.id}\">{message.from_user.full_name}</a>"
            ),
            parse_mode="HTML"
        )

        await message.reply("✅ Сообщение отправлено в PRO-группу")

    except TelegramBadRequest as e:
        await message.reply(f"❌ Ошибка при пересылке: {e.message}")


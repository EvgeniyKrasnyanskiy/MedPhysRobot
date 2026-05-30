# handlers/moderation.py

import html
import re
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
from utils.config import ADMIN_GROUP_ID, MEDPHYSPRO_GROUP_ID, MEDPHYSPRO_CHANNEL_ID, LOG_CHANNEL_ID, MEDPHYSPRO_GROUP_TOPIC_ID
from utils.logger import get_logger
from datetime import datetime, timedelta, timezone
import asyncio

from utils.sender import send_content_to_group
from utils.topics import resolve_topic_id_by_keywords

router = Router()
logger = get_logger("moderation")
logger.info("[MOD] moderation.py загружен")

MAX_CAPTION = 1024
MAX_TEXT = 4096  # лимит для обычного send_message

def split_text(text: str, limit: int) -> list[str]:
    """Разбивает текст на части по limit символов."""
    return [text[i:i+limit] for i in range(0, len(text), limit)]

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


def parse_mute_duration(text: str) -> timedelta | None:
    """Парсит аргумент времени из текста сообщения команды.
    Примеры:
      /mute -> дефолт 2 часа
      /mute 30m -> 30 минут
      /mute 5h -> 5 часов
      /mute 5 -> 5 часов (дефолтная единица при отсутствии суффикса)
      /mute 2d -> 2 дня
      /mute 1w -> 1 неделя
    Если формат неверный, возвращает None.
    """
    if not text:
        return timedelta(hours=2)
        
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return timedelta(hours=2)
        
    arg = parts[1].strip().lower()
    if not arg:
        return timedelta(hours=2)

    match = re.match(r"^(\d+)([mhdw])?$", arg)
    if not match:
        return None
        
    value = int(match.group(1))
    unit = match.group(2)
    
    if not unit:
        return timedelta(hours=value)
    elif unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    elif unit == 'w':
        return timedelta(weeks=value)
        
    return None


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

    duration = parse_mute_duration(message.text)
    if duration is None:
        info = await message.reply("❗ Неверный формат времени. Используйте: `/mute [время][m/h/d/w]`, например `/mute 2h` или `/mute 30m`.")
        await asyncio.sleep(5)
        try:
            await message.delete()
            await info.delete()
        except Exception as e:
            logger.warning(f"[MOD] Не удалось удалить сообщения при ошибке mute: {e}")
        return

    muted_until = (datetime.now(timezone.utc) + duration).isoformat()
    mute_user(user_id, muted_until=muted_until)

    duration_str = message.text.split(maxsplit=1)[1].strip() if len(message.text.split(maxsplit=1)) > 1 else "2h"
    logger.info(f"[MOD] Замьючен user_id={user_id} до {muted_until} UTC (на {duration_str})")
    await message.reply(f"🔇 Пользователь {user_id} замьючен до {muted_until} UTC (на {duration_str}).")

    try:
        await bot.send_message(user_id, f"🔇 Вы были временно замьючены до {muted_until} UTC (на {duration_str}).")
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

    banned_at = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
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


# ↪️ /send_to_pro_group
@router.message(Command("send_to_pro_group"), F.chat.id == ADMIN_GROUP_ID, F.reply_to_message)
async def cmd_send_to_pro_group(message: Message):
    logger.info(f"[MOD] cmd_send_to_pro_group вызван: from_msg_id={message.reply_to_message.message_id}, by={message.from_user.id}")
    if message.chat.id != ADMIN_GROUP_ID:
        return

    if not message.reply_to_message:
        await reply_required(message, "/send_to_pro_group")
        return

    await send_to_pro_group(message)


async def send_to_pro_group(message: Message):
    try:
        # Добавлено: Определяем thread_id по ключевым словам, как в новостях
        tid = resolve_topic_id_by_keywords(message.reply_to_message)
        if tid is None and MEDPHYSPRO_GROUP_TOPIC_ID and int(MEDPHYSPRO_GROUP_TOPIC_ID) > 0:
            tid = MEDPHYSPRO_GROUP_TOPIC_ID  # Fallback на дефолтный, если ключевых слов нет
        suffix = ""  # Или другой, если нужно
        logger.info(f"[MOD] send_to_pro_group: tid={tid}, suffix='{suffix}', reply_type={message.reply_to_message.content_type}")

        sent_messages = await send_content_to_group(
            message=message.reply_to_message,
            bot=message.bot,
            chat_id=MEDPHYSPRO_GROUP_ID,
            thread_id=tid,
            suffix=suffix
        )

        if not sent_messages:
            logger.warning("[MOD] Не удалось переслать через send_content, fallback на forward")
            forwarded = await message.bot.forward_message(
                chat_id=MEDPHYSPRO_GROUP_ID,
                from_chat_id=message.reply_to_message.chat.id,
                message_id=message.reply_to_message.message_id,
                message_thread_id=tid
            )
            sent_messages = [forwarded]

        ids_str = ", ".join(str(m.message_id) for m in sent_messages)
        logger.info(
            f"[MOD] Переслано в PRO-группу: from_msg_id={message.reply_to_message.message_id}, "
            f"to_msg_ids=[{ids_str}], by={message.from_user.id}, thread_id={tid}, suffix='{suffix}'"
        )

        await message.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=(
                f"📤 <b>Переслано из админской группы в PRO-группу</b>\n"
                f"🧵 thread_id: <code>{tid}</code>\n"
                f"↪️ Исходное msg_id: <code>{message.reply_to_message.message_id}</code>\n"
                f"📨 Новые msg_id: <code>{ids_str}</code>\n"
                f"👤 Отправитель: <a href=\"tg://user?id={message.from_user.id}\">{html.escape(message.from_user.full_name)}</a>"
            ),
            parse_mode="HTML"
        )

        await message.reply("✅ Сообщение отправлено в PRO-группу")

    except TelegramBadRequest as e:
        logger.error(f"[MOD] Ошибка: {e}")
        await message.reply(f"❌ Ошибка при пересылке: {e.message}")
    except Exception as e:
        logger.error(f"[MOD] Неизвестная ошибка: {e}")
        await message.reply("❌ Неизвестная ошибка.")


# 📢 /send_to_channel
@router.message(Command("send_to_channel"), F.chat.id == ADMIN_GROUP_ID, F.reply_to_message)
async def cmd_send_to_channel(message: Message):
    logger.info(f"[MOD] cmd_send_to_channel вызван: from_msg_id={message.reply_to_message.message_id}, by={message.from_user.id}")
    if message.chat.id != ADMIN_GROUP_ID:
        return

    if not message.reply_to_message:
        await reply_required(message, "/send_to_channel")
        return

    text_or_caption = message.text or message.caption or ""
    parts = text_or_caption.split(maxsplit=1)
    args = parts[1].strip() if len(parts) > 1 else ""

    await send_to_channel(message, args)


def extract_message_id_from_link(text: str) -> int | None:
    text = text.strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    match = re.search(r'(?:/|post=)(\d+)(?:\?|$)', text)
    if match:
        return int(match.group(1))
    return None


def make_channel_post_link(chat_id: int, msg_id: int, username: str | None = None) -> str:
    if username:
        return f"https://t.me/{username.lstrip('@')}/{msg_id}"
    clean_id = str(chat_id)
    if clean_id.startswith("-100"):
        clean_id = clean_id[4:]
    elif clean_id.startswith("-"):
        clean_id = clean_id[1:]
    return f"https://t.me/c/{clean_id}/{msg_id}"


async def send_to_channel(message: Message, args: str):
    target_message_id = extract_message_id_from_link(args)

    if target_message_id is not None:
        # Режим редактирования существующего сообщения
        try:
            logger.info(f"[MOD] Попытка редактирования сообщения в канале: msg_id={target_message_id}, by={message.from_user.id}")

            reply = message.reply_to_message
            has_media = bool(
                reply.photo or
                reply.video or
                reply.document or
                reply.audio or
                reply.animation
            )

            new_text = reply.html_text or ""

            if has_media:
                await message.bot.edit_message_caption(
                    chat_id=MEDPHYSPRO_CHANNEL_ID,
                    message_id=target_message_id,
                    caption=new_text,
                    parse_mode="HTML"
                )
            else:
                await message.bot.edit_message_text(
                    chat_id=MEDPHYSPRO_CHANNEL_ID,
                    message_id=target_message_id,
                    text=new_text,
                    parse_mode="HTML"
                )

            from utils.config import MEDPHYSPRO_CHANNEL_USERNAME
            post_link = make_channel_post_link(MEDPHYSPRO_CHANNEL_ID, target_message_id, MEDPHYSPRO_CHANNEL_USERNAME)

            await message.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=(
                    f"📝 <b>Отредактировано сообщение в канале</b>\n"
                    f"↪️ Исходное msg_id (реплай): <code>{message.reply_to_message.message_id}</code>\n"
                    f"✏️ Сообщение в канале: <a href=\"{post_link}\">ID {target_message_id}</a>\n"
                    f"👤 Редактор: <a href=\"tg://user?id={message.from_user.id}\">{html.escape(message.from_user.full_name)}</a>"
                ),
                parse_mode="HTML"
            )

            await message.reply("✅ Сообщение в канале успешно отредактировано")

        except TelegramBadRequest as e:
            logger.error(f"[MOD] Ошибка редактирования в канале: {e}")
            await message.reply(
                f"❌ Не удалось отредактировать сообщение в канале: {e.message}\n"
                f"Убедитесь, что сообщение было отправлено этим ботом и оно не слишком старое."
            )
        except Exception as e:
            logger.error(f"[MOD] Неизвестная ошибка при редактировании в канале: {e}")
            await message.reply("❌ Неизвестная ошибка при редактировании сообщения.")

    else:
        # Стандартный режим отправки нового сообщения
        try:
            sent_messages = await send_content_to_group(
                message=message.reply_to_message,
                bot=message.bot,
                chat_id=MEDPHYSPRO_CHANNEL_ID,
            )

            if not sent_messages:
                logger.warning("[MOD] Не удалось отправить через send_content, fallback на forward")
                forwarded = await message.bot.forward_message(
                    chat_id=MEDPHYSPRO_CHANNEL_ID,
                    from_chat_id=message.reply_to_message.chat.id,
                    message_id=message.reply_to_message.message_id,
                )
                sent_messages = [forwarded]

            ids_str = ", ".join(str(m.message_id) for m in sent_messages)
            logger.info(
                f"[MOD] Переслано в канал: from_msg_id={message.reply_to_message.message_id}, "
                f"to_msg_ids=[{ids_str}], by={message.from_user.id}"
            )

            await message.bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=(
                    f"📢 <b>Переслано из админской группы в канал</b>\n"
                    f"↪️ Исходное msg_id: <code>{message.reply_to_message.message_id}</code>\n"
                    f"📨 Новые msg_id: <code>{ids_str}</code>\n"
                    f"👤 Отправитель: <a href=\"tg://user?id={message.from_user.id}\">{html.escape(message.from_user.full_name)}</a>"
                ),
                parse_mode="HTML"
            )

            await message.reply("✅ Сообщение отправлено в канал")

        except TelegramBadRequest as e:
            logger.error(f"[MOD] Ошибка отправки в канал: {e}")
            await message.reply(f"❌ Ошибка при пересылке в канал: {e.message}")
        except Exception as e:
            logger.error(f"[MOD] Неизвестная ошибка при отправке в канал: {e}")
            await message.reply("❌ Неизвестная ошибка.")

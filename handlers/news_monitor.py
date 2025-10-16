# handlers/news_monitor.py

import sqlite3
import hashlib
from datetime import timedelta, datetime

from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest
from utils.config import MEDPHYSPRO_CHANNEL_ID, MEDPHYSPRO_GROUP_ID, MEDPHYSPRO_GROUP_TOPIC_ID, DB_PATH, \
    MEDPHYSPRO_CHANNEL_USERNAME
from utils.logger import setup_logger

router = Router()
logger = setup_logger("news_monitor")

def resolve_thread_id(raw_id: str | None) -> int | None:
    try:
        if not raw_id or str(raw_id).strip() in ("", "0", "1"):
            return None
        thread_id = int(raw_id)
        if thread_id <= 1:
            return None
        return thread_id
    except ValueError:
        logger.warning(f"[NEWS] Некорректный MEDPHYSPRO_GROUP_TOPIC_ID: {raw_id}")
        return None

def init_forwarded_news_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forwarded_news (
            message_id INTEGER PRIMARY KEY,
            content_hash TEXT NOT NULL,
            group_msg_id INTEGER,
            forwarded_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def hash_message_content(message: Message) -> str:
    content = (message.text or "") + (message.caption or "")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def is_hash_already_forwarded(content_hash: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM forwarded_news WHERE content_hash = ?", (content_hash,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def save_forwarded_news(message_id: int, content_hash: str, group_msg_id: int = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO forwarded_news (message_id, content_hash, group_msg_id)
        VALUES (?, ?, ?)
    """, (message_id, content_hash, group_msg_id))
    conn.commit()
    conn.close()

def get_group_msg_id(message_id: int) -> int | None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT group_msg_id FROM forwarded_news WHERE message_id = ?", (message_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def contains_deleted_marker(text: str | None) -> bool:
    return text and "deleted" in text.lower()

init_forwarded_news_table()

@router.channel_post()
async def forward_news(message: Message, bot: Bot):
    if message.chat.id != MEDPHYSPRO_CHANNEL_ID:
        return

    content_hash = hash_message_content(message)

    if is_hash_already_forwarded(content_hash):
        logger.info(f"[NEWS] Пропущено по хешу: message_id={message.message_id}")
        return

    thread_id = resolve_thread_id(MEDPHYSPRO_GROUP_TOPIC_ID)
    suffix = f"\n\nИсточник: @{MEDPHYSPRO_CHANNEL_USERNAME}"

    try:
        sent = None

        if message.photo:
            sent = await bot.send_photo(
                chat_id=MEDPHYSPRO_GROUP_ID,
                photo=message.photo[-1].file_id,
                caption=(message.caption or "") + suffix,
                message_thread_id=thread_id
            )
        elif message.video:
            sent = await bot.send_video(
                chat_id=MEDPHYSPRO_GROUP_ID,
                video=message.video.file_id,
                caption=(message.caption or "") + suffix,
                message_thread_id=thread_id
            )
        elif message.document:
            sent = await bot.send_document(
                chat_id=MEDPHYSPRO_GROUP_ID,
                document=message.document.file_id,
                caption=(message.caption or "") + suffix,
                message_thread_id=thread_id
            )
        elif message.text:
            sent = await bot.send_message(
                chat_id=MEDPHYSPRO_GROUP_ID,
                text=message.text + suffix,
                message_thread_id=thread_id
            )
        else:
            logger.warning(f"[NEWS] Неизвестный тип сообщения: message_id={message.message_id}")
            return

        save_forwarded_news(message.message_id, content_hash, group_msg_id=sent.message_id)
        logger.info(f"[NEWS] Отправлено: message_id={message.message_id}, group_msg_id={sent.message_id}")
    except Exception as e:
        logger.exception(f"[NEWS] Ошибка при отправке: {e}")

@router.edited_channel_post()
async def handle_edited_news(message: Message, bot: Bot):
    group_msg_id = get_group_msg_id(message.message_id)
    if not group_msg_id:
        logger.info(f"[NEWS] Нет group_msg_id для message_id={message.message_id}")
        return

    # Удаление по пустому содержимому или маркеру "deleted"
    if (
        not message.text and not message.caption
    ) or (
        contains_deleted_marker(message.text) or contains_deleted_marker(message.caption)
    ):
        try:
            await bot.delete_message(chat_id=MEDPHYSPRO_GROUP_ID, message_id=group_msg_id)
            logger.info(f"[NEWS] Удалено сообщение в группе: message_id={group_msg_id} (маркер или пустое)")
        except Exception as e:
            logger.error(f"[NEWS] Ошибка при удалении: {e}")
        return

    suffix = f"\n\nИсточник: @{MEDPHYSPRO_CHANNEL_USERNAME}"

    try:
        if message.text:
            await bot.edit_message_text(
                chat_id=MEDPHYSPRO_GROUP_ID,
                message_id=group_msg_id,
                text=message.text + suffix
            )
        elif message.caption:
            await bot.edit_message_caption(
                chat_id=MEDPHYSPRO_GROUP_ID,
                message_id=group_msg_id,
                caption=message.caption + suffix
            )
        else:
            logger.warning(f"[NEWS] Не удалось отредактировать: message_id={message.message_id} — нет текста или caption")
            return

        logger.info(f"[NEWS] Обновлено сообщение: message_id={message.message_id}")
    except TelegramBadRequest as e:
        logger.warning(f"[NEWS] Ошибка Telegram при редактировании: {e}")
    except Exception as e:
        logger.exception(f"[NEWS] Неожиданная ошибка при редактировании: {e}")

def cleanup_forwarded_news(days: int = 7):
    threshold = datetime.utcnow() - timedelta(days=days)
    iso_threshold = threshold.isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM forwarded_news WHERE forwarded_at < ?", (iso_threshold,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    logger.info(f"[DB] Очистка forwarded_news: удалено {deleted} записей старше {iso_threshold}")



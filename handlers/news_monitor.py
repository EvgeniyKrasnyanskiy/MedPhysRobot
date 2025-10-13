# handlers/news_monitor.py

import sqlite3
import hashlib
from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest
from utils.config import SOURCE_CHANNEL_ID, TARGET_GROUP_ID, TARGET_TOPIC_ID, DB_PATH
from utils.logger import setup_logger

router = Router()
logger = setup_logger("news_monitor")

def init_forwarded_news_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forwarded_news (
            message_id INTEGER PRIMARY KEY,
            content_hash TEXT NOT NULL,
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

def save_forwarded_news(message_id: int, content_hash: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO forwarded_news (message_id, content_hash)
        VALUES (?, ?)
    """, (message_id, content_hash))
    conn.commit()
    conn.close()

init_forwarded_news_table()

@router.channel_post()
async def forward_news(message: Message, bot: Bot):
    if message.chat.id != SOURCE_CHANNEL_ID:
        return

    content_hash = hash_message_content(message)

    if is_hash_already_forwarded(content_hash):
        logger.info(f"[NEWS] Пропущено по хешу: message_id={message.message_id}")
        return

    # Определение thread_id и режима пересылки
    use_forward = False
    thread_id = None

    if not TARGET_TOPIC_ID or str(TARGET_TOPIC_ID).strip() in ("", "0", "1"):
        use_forward = True
    else:
        try:
            thread_id = int(TARGET_TOPIC_ID)
            if thread_id <= 1:
                use_forward = True
                thread_id = None
        except ValueError:
            logger.warning(f"[NEWS] Некорректный TARGET_TOPIC_ID: {TARGET_TOPIC_ID}")
            use_forward = True
            thread_id = None

    try:
        if use_forward:
            await message.forward(chat_id=TARGET_GROUP_ID)
            logger.info(f"[NEWS] Переслано через forward(): message_id={message.message_id}")
        else:
            # Добавление источника
            caption = message.caption or ""
            if caption:
                caption += "\n\nИсточник: @MedPhysProChannel"
            else:
                caption = "Источник: @MedPhysProChannel"

            if message.photo:
                await bot.send_photo(
                    chat_id=TARGET_GROUP_ID,
                    photo=message.photo[-1].file_id,
                    caption=caption,
                    message_thread_id=thread_id
                )
            elif message.video:
                await bot.send_video(
                    chat_id=TARGET_GROUP_ID,
                    video=message.video.file_id,
                    caption=caption,
                    message_thread_id=thread_id
                )
            elif message.document:
                await bot.send_document(
                    chat_id=TARGET_GROUP_ID,
                    document=message.document.file_id,
                    caption=caption,
                    message_thread_id=thread_id
                )
            elif message.text:
                await bot.send_message(
                    chat_id=TARGET_GROUP_ID,
                    text=message.text + "\n\nИсточник: @MedPhysProChannel",
                    message_thread_id=thread_id
                )
            else:
                # fallback: copy_message без подписи
                await bot.copy_message(
                    chat_id=TARGET_GROUP_ID,
                    from_chat_id=SOURCE_CHANNEL_ID,
                    message_id=message.message_id,
                    message_thread_id=thread_id
                )

            logger.info(f"[NEWS] Скопировано через copy_message(): message_id={message.message_id}, thread_id={thread_id}")

        save_forwarded_news(message.message_id, content_hash)
    except TelegramBadRequest as e:
        logger.warning(f"[NEWS] Ошибка при пересылке: {e}")
    except Exception as e:
        logger.exception(f"[NEWS] Неожиданная ошибка: {e}")


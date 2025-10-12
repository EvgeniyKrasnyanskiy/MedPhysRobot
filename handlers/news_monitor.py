# handlers/news_monitor.py

import sqlite3
import hashlib
from aiogram import Router, Bot
from aiogram.types import Message
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

    try:
        await message.forward(
            chat_id=TARGET_GROUP_ID,
            message_thread_id=TARGET_TOPIC_ID
        )
        save_forwarded_news(message.message_id, content_hash)
        logger.info(f"[NEWS] Переслано сообщение из канала: message_id={message.message_id}")
    except Exception as e:
        logger.warning(f"[NEWS] Ошибка при пересылке новости: {e}")

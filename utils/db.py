# utils/db.py

import sqlite3
import os
from datetime import datetime, timedelta
from utils.logger import get_logger
from utils.config import DB_PATH

logger = get_logger("db")
logger.info("[DB] db.py загружен")

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Таблица пересылок
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relay_map (
            forwarded_id INTEGER PRIMARY KEY,
            original_user_id INTEGER NOT NULL,
            original_message_id INTEGER NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            has_sent INTEGER DEFAULT 0
        )
    """)

    # Таблица пользователей с ограничениями
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS moderation (
            user_id INTEGER PRIMARY KEY,
            banned INTEGER DEFAULT 0,
            banned_at TEXT DEFAULT NULL,
            muted_until TEXT DEFAULT NULL
        )
    """)

    # Таблица пересланных новостей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forwarded_news (
            message_id INTEGER PRIMARY KEY,
            content_hash TEXT NOT NULL,
            forwarded_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Таблица ответов админов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reply_map (
            admin_msg_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            user_msg_id INTEGER NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

def save_mapping(forwarded_id: int, user_id: int, original_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO relay_map (forwarded_id, original_user_id, original_message_id)
        VALUES (?, ?, ?)
    """, (forwarded_id, user_id, original_id))
    conn.commit()
    conn.close()

def get_user_by_forwarded(forwarded_id: int) -> int | None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT original_user_id FROM relay_map WHERE forwarded_id = ?", (forwarded_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def user_exists(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT has_sent FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_user_sent(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, has_sent)
        VALUES (?, 1)
        ON CONFLICT(user_id) DO UPDATE SET has_sent = 1
    """, (user_id,))
    conn.commit()
    conn.close()

def mute_user(user_id: int, muted_until: str):
    logger = get_logger("db")
    logger.info(f"[DB] mute_user: user_id={user_id}, until={muted_until}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO moderation (user_id, muted_until)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET muted_until = ?
    """, (user_id, muted_until, muted_until))
    conn.commit()
    conn.close()

def unmute_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE moderation SET muted_until = NULL WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def ban_user(user_id: int, banned_at: str):
    logger = get_logger("db")
    logger.info(f"[DB] ban_user: user_id={user_id}, banned_at={banned_at}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO moderation (user_id, banned, banned_at)
        VALUES (?, 1, ?)
        ON CONFLICT(user_id) DO UPDATE SET banned = 1, banned_at = ?
    """, (user_id, banned_at, banned_at))
    conn.commit()
    conn.close()

def unban_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE moderation SET banned = 0, banned_at = NULL WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_banned(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT banned FROM moderation WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

def is_muted(user_id: int) -> bool:
    logger = get_logger("db")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT muted_until FROM moderation WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    logger.info(f"[DB] is_muted: user_id={user_id}, muted_until={result}")

    if result and result[0]:
        try:
            until = datetime.fromisoformat(result[0])
            if datetime.utcnow() >= until:
                unmute_user(user_id)
                logger.info(f"[DB] mute expired — user_id={user_id} размьючен автоматически")
                return False
            return True
        except ValueError:
            return False
    return False

def get_admin_msg_id(user_id: int, user_msg_id: int) -> int | None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT forwarded_id FROM relay_map
        WHERE original_user_id = ? AND original_message_id = ?
    """, (user_id, user_msg_id))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def save_reply_mapping(admin_msg_id: int, user_id: int, user_msg_id: int):
    logger = get_logger("db")  # ← добавляем логгер
    logger.info(f"[DB] save_reply_mapping: admin_msg_id={admin_msg_id}, user_id={user_id}, user_msg_id={user_msg_id}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO reply_map (admin_msg_id, user_id, user_msg_id)
        VALUES (?, ?, ?)
    """, (admin_msg_id, user_id, user_msg_id))
    conn.commit()
    conn.close()

def get_user_reply_msg(admin_msg_id: int) -> tuple[int, int] | None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, user_msg_id FROM reply_map WHERE admin_msg_id = ?
    """, (admin_msg_id,))
    result = cursor.fetchone()
    conn.close()
    return result if result else None

def get_user_status(user_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT banned, banned_at, muted_until FROM moderation WHERE user_id = ?
    """, (user_id,))
    result = cursor.fetchone()
    conn.close()

    status = {
        "banned": False,
        "banned_at": None,
        "muted": False,
        "muted_until": None
    }

    if result:
        status["banned"] = result[0] == 1
        status["banned_at"] = result[1]
        if result[2]:
            try:
                muted_until = datetime.fromisoformat(result[2])
                status["muted"] = datetime.utcnow() < muted_until
                status["muted_until"] = result[2]
            except ValueError:
                status["muted"] = False

    return status

def cleanup_old_mappings(days: int = 2):
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM relay_map WHERE timestamp < ?", (cutoff,))
    cursor.execute("DELETE FROM reply_map WHERE timestamp < ?", (cutoff,))
    conn.commit()
    conn.close()

    logger = get_logger("db")
    logger.info(f"[DB] Очистка старых связей: удалено всё старше {cutoff}")

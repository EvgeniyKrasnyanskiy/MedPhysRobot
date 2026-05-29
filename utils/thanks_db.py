# utils/thanks_db.py

import sqlite3
from utils.config import DB_PATH
from utils.logger import get_logger

logger = get_logger("thanks_db")
logger.info("[THANKS_DB] thanks_db.py загружен")

def init_thanks_table():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS thanks (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                count INTEGER DEFAULT 0
            )
        """)
        conn.commit()

def increment_thanks(user_id: int, name: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO thanks (user_id, name, count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                count = count + 1,
                name = excluded.name
        """, (user_id, name))
        conn.commit()

def get_top_thanked(limit: int = 10) -> list[tuple[str, int]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, count FROM thanks
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        result = cursor.fetchall()
    return result

init_thanks_table()

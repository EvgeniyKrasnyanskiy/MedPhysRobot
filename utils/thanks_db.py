# utils/thanks_db.py

import sqlite3
from utils.config import DB_PATH

def init_thanks_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS thanks (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def increment_thanks(user_id: int, name: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO thanks (user_id, name, count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id) DO UPDATE SET
            count = count + 1,
            name = excluded.name
    """, (user_id, name))
    conn.commit()
    conn.close()

def get_top_thanked(limit: int = 10) -> list[tuple[str, int]]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, count FROM thanks
        ORDER BY count DESC
        LIMIT ?
    """, (limit,))
    result = cursor.fetchall()
    conn.close()
    return result

init_thanks_table()

import aiosqlite
from config import DB_PATH
import os

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id        INTEGER PRIMARY KEY REFERENCES users(user_id),
                is_subscribed  INTEGER DEFAULT 1,
                subscribed_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sent_news (
                url      TEXT PRIMARY KEY,
                sent_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS lesson_progress (
                user_id    INTEGER REFERENCES users(user_id),
                lesson_id  INTEGER,
                done_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, lesson_id)
            );

            CREATE TABLE IF NOT EXISTS quiz_results (
                user_id     INTEGER REFERENCES users(user_id),
                correct     INTEGER DEFAULT 0,
                total       INTEGER DEFAULT 0,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id)
            );
        """)
        await db.commit()

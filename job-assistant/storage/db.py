"""Хранение профилей, режима и истории диалога в SQLite."""
import json

import aiosqlite

import config


async def init_db() -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                profile TEXT DEFAULT '',
                mode    TEXT DEFAULT 'assistant',
                history TEXT DEFAULT '[]'
            )
            """
        )
        await db.commit()


async def get_user(user_id: int) -> dict:
    """Возвращает данные пользователя, создавая запись при первом обращении."""
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
        await db.commit()
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
    return {
        "profile": row["profile"] or "",
        "mode": row["mode"] or "assistant",
        "history": json.loads(row["history"] or "[]"),
    }


async def set_profile(user_id: int, profile: str) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
        await db.execute("UPDATE users SET profile = ? WHERE user_id = ?", (profile, user_id))
        await db.commit()


async def set_mode(user_id: int, mode: str) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
        await db.execute("UPDATE users SET mode = ? WHERE user_id = ?", (mode, user_id))
        await db.commit()


async def save_history(user_id: int, messages: list) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "UPDATE users SET history = ? WHERE user_id = ?",
            (json.dumps(messages, ensure_ascii=False), user_id),
        )
        await db.commit()


async def reset_history(user_id: int) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE users SET history = '[]' WHERE user_id = ?", (user_id,))
        await db.commit()


def _is_clean_user_start(message: dict) -> bool:
    """Первое сообщение должно быть user-репликой и НЕ tool_result.

    Иначе API вернёт ошибку (tool_result без предшествующего tool_use).
    """
    if message.get("role") != "user":
        return False
    content = message.get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list) and content:
        return content[0].get("type") != "tool_result"
    return False


def trim_history(messages: list, max_len: int = config.MAX_HISTORY_MESSAGES) -> list:
    """Обрезает историю, не нарушая пары tool_use/tool_result и старт с user."""
    msgs = messages[-max_len:] if len(messages) > max_len else list(messages)
    while msgs and not _is_clean_user_start(msgs[0]):
        msgs = msgs[1:]
    return msgs

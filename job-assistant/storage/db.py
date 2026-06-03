"""Хранение профилей, режима, истории диалога и трекера откликов в SQLite."""
import json
from datetime import datetime, timezone

import aiosqlite

import config

# Статусы отклика: код -> человекочитаемая подпись
STATUSES = {
    "saved": "сохранено",
    "applied": "отправлено",
    "interview": "собеседование",
    "offer": "оффер",
    "rejected": "отказ",
}


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
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                title      TEXT NOT NULL,
                company    TEXT DEFAULT '',
                url        TEXT DEFAULT '',
                status     TEXT DEFAULT 'saved',
                note       TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT
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


# --- Трекер откликов ---

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def add_application(
    user_id: int,
    title: str,
    company: str = "",
    url: str = "",
    status: str = "saved",
    note: str = "",
) -> int:
    if status not in STATUSES:
        status = "saved"
    ts = _now()
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO applications (user_id, title, company, url, status, note, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, title, company or "", url or "", status, note or "", ts, ts),
        )
        await db.commit()
        return cur.lastrowid


async def list_applications(user_id: int) -> list[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM applications WHERE user_id = ? ORDER BY id",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def update_application(
    user_id: int,
    application_id: int,
    status: str | None = None,
    note: str | None = None,
) -> bool:
    fields, params = [], []
    if status is not None:
        if status not in STATUSES:
            return False
        fields.append("status = ?")
        params.append(status)
    if note is not None:
        fields.append("note = ?")
        params.append(note)
    if not fields:
        return False
    fields.append("updated_at = ?")
    params.append(_now())
    params.extend([application_id, user_id])
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            f"UPDATE applications SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
            params,
        )
        await db.commit()
        return cur.rowcount > 0


async def delete_application(user_id: int, application_id: int) -> bool:
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM applications WHERE id = ? AND user_id = ?",
            (application_id, user_id),
        )
        await db.commit()
        return cur.rowcount > 0

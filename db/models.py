import aiosqlite
from config import DB_PATH

_user_cache: set[int] = set()


async def upsert_user(user_id: int, username: str | None, first_name: str):
    if user_id in _user_cache:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name
            """,
            (user_id, username, first_name),
        )
        await db.commit()
    _user_cache.add(user_id)


# --- Подписки ---

async def subscribe(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO subscriptions (user_id, is_subscribed)
            VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET is_subscribed = 1
            """,
            (user_id,),
        )
        await db.commit()


async def unsubscribe(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscriptions SET is_subscribed = 0 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def is_subscribed(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT is_subscribed FROM subscriptions WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row and row[0])


async def get_subscribers() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM subscriptions WHERE is_subscribed = 1"
        ) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]


# --- Дедупликация новостей ---

async def is_news_sent(url: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM sent_news WHERE url = ?", (url,)
        ) as cursor:
            return await cursor.fetchone() is not None


async def get_sent_urls(urls: list[str]) -> set[str]:
    if not urls:
        return set()
    placeholders = ",".join("?" * len(urls))
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            f"SELECT url FROM sent_news WHERE url IN ({placeholders})", urls
        ) as cursor:
            rows = await cursor.fetchall()
            return {r[0] for r in rows}


# --- Прогресс уроков ---

async def mark_lesson_done(user_id: int, lesson_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO lesson_progress (user_id, lesson_id) VALUES (?, ?)",
            (user_id, lesson_id),
        )
        await db.commit()


async def get_done_lessons(user_id: int) -> set[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT lesson_id FROM lesson_progress WHERE user_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return {r[0] for r in rows}


# --- Результаты квизов ---

async def update_quiz_result(user_id: int, correct: int, total: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO quiz_results (user_id, correct, total)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                correct    = correct + excluded.correct,
                total      = total + excluded.total,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, correct, total),
        )
        await db.commit()


async def get_quiz_result(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT correct, total FROM quiz_results WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"correct": row[0], "total": row[1]}
            return {"correct": 0, "total": 0}


async def mark_news_sent(urls: list[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "INSERT OR IGNORE INTO sent_news (url) VALUES (?)",
            [(u,) for u in urls],
        )
        # Оставляем только последние 2000 записей
        await db.execute(
            """
            DELETE FROM sent_news WHERE url NOT IN (
                SELECT url FROM sent_news ORDER BY sent_at DESC LIMIT 2000
            )
            """
        )
        await db.commit()

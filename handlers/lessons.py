import json
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from db.models import upsert_user, mark_lesson_done, get_done_lessons

_FILE = Path(__file__).parent.parent / "data" / "lessons.json"


def _load() -> list[dict]:
    with open(_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _lessons_keyboard(done: set[int]) -> InlineKeyboardMarkup:
    lessons = _load()
    buttons = []
    for lesson in lessons:
        mark = "✅" if lesson["id"] in done else "📖"
        buttons.append([InlineKeyboardButton(
            f"{mark} {lesson['id']}. {lesson['title']}",
            callback_data=f"lesson_{lesson['id']}"
        )])
    buttons.append([InlineKeyboardButton("◀️ Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def _lesson_keyboard(lesson_id: int, total: int) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    if lesson_id > 1:
        row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"lesson_{lesson_id - 1}"))
    row.append(InlineKeyboardButton("✅ Изучено", callback_data=f"lesson_done_{lesson_id}"))
    if lesson_id < total:
        row.append(InlineKeyboardButton("➡️ Далее", callback_data=f"lesson_{lesson_id + 1}"))
    buttons.append(row)
    buttons.append([InlineKeyboardButton("📋 Список уроков", callback_data="lessons_list")])
    return InlineKeyboardMarkup(buttons)


async def cmd_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)
    done = await get_done_lessons(user.id)
    await update.message.reply_text(
        f"📚 *Уроки по SQL*\n\nПройдено: {len(done)}/{len(_load())}\n\nВыбери урок:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_lessons_keyboard(done),
    )


async def show_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int):
    query = update.callback_query
    lessons = _load()
    lesson = next((l for l in lessons if l["id"] == lesson_id), None)
    if not lesson:
        await query.answer("Урок не найден.")
        return

    text = (
        f"📖 *Урок {lesson['id']}: {lesson['title']}*\n\n"
        f"{lesson['theory']}\n\n"
        f"*Пример:*\n```sql\n{lesson['example']}\n```\n\n"
        f"*Задача:*\n_{lesson['task']}_"
    )
    await query.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_lesson_keyboard(lesson_id, len(lessons)),
    )


async def show_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int):
    query = update.callback_query
    user = query.from_user
    lessons = _load()
    lesson = next((l for l in lessons if l["id"] == lesson_id), None)
    if not lesson:
        return

    await mark_lesson_done(user.id, lesson_id)
    done = await get_done_lessons(user.id)

    await query.answer("Урок отмечен как пройденный! ✅")
    await query.message.edit_text(
        f"✅ *Ответ на задачу урока {lesson_id}:*\n\n"
        f"```sql\n{lesson['answer']}\n```\n\n"
        f"Пройдено уроков: {len(done)}/{len(lessons)}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 К списку уроков", callback_data="lessons_list")],
        ]),
    )


async def show_lessons_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    done = await get_done_lessons(user.id)
    await query.message.edit_text(
        f"📚 *Уроки по SQL*\n\nПройдено: {len(done)}/{len(_load())}\n\nВыбери урок:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_lessons_keyboard(done),
    )

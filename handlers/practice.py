import json
import random
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from db.models import upsert_user

_FILE = Path(__file__).parent.parent / "data" / "practice.json"

LEVELS = {
    "beginner": "Начинающий 🟢",
    "medium": "Средний 🟡",
    "advanced": "Продвинутый 🔴",
}


def _load() -> list[dict]:
    with open(_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _practice_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("🟢 Начинающий", callback_data="practice_beginner")],
        [InlineKeyboardButton("🟡 Средний", callback_data="practice_medium")],
        [InlineKeyboardButton("🔴 Продвинутый", callback_data="practice_advanced")],
        [InlineKeyboardButton("🎲 Случайная задача", callback_data="practice_random")],
        [InlineKeyboardButton("◀️ Главное меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(buttons)


def _task_keyboard(task_id: int, show_hint: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    if not show_hint:
        buttons.append([InlineKeyboardButton("💡 Подсказка", callback_data=f"practice_hint_{task_id}")])
    buttons.append([InlineKeyboardButton("✅ Показать решение", callback_data=f"practice_solution_{task_id}")])
    buttons.append([InlineKeyboardButton("🎲 Другая задача", callback_data="practice_random")])
    buttons.append([InlineKeyboardButton("◀️ К выбору уровня", callback_data="practice_menu")])
    return InlineKeyboardMarkup(buttons)


def _format_task(task: dict, show_hint: bool = False, show_solution: bool = False) -> str:
    text = (
        f"💪 *Задача #{task['id']} — {task['level_label']}*\n\n"
        f"*{task['title']}*\n\n"
        f"{task['description']}"
    )
    if show_hint:
        text += f"\n\n💡 *Подсказка:* _{task['hint']}_"
    if show_solution:
        text += f"\n\n✅ *Решение:*\n```sql\n{task['solution']}\n```"
    return text


async def cmd_practice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)
    await update.message.reply_text(
        "💪 *Практика SQL*\n\nВыбери уровень сложности:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_practice_menu_keyboard(),
    )


async def show_practice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text(
        "💪 *Практика SQL*\n\nВыбери уровень сложности:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_practice_menu_keyboard(),
    )


async def show_task_by_level(update: Update, context: ContextTypes.DEFAULT_TYPE, level: str):
    query = update.callback_query
    tasks = [t for t in _load() if t["level"] == level]
    if not tasks:
        await query.answer("Задачи не найдены.")
        return
    task = random.choice(tasks)
    await query.message.edit_text(
        _format_task(task),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_task_keyboard(task["id"]),
    )


async def show_random_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task = random.choice(_load())
    await query.message.edit_text(
        _format_task(task),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_task_keyboard(task["id"]),
    )


async def show_hint(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
    query = update.callback_query
    task = next((t for t in _load() if t["id"] == task_id), None)
    if not task:
        return
    await query.message.edit_text(
        _format_task(task, show_hint=True),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_task_keyboard(task_id, show_hint=True),
    )


async def show_solution(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
    query = update.callback_query
    task = next((t for t in _load() if t["id"] == task_id), None)
    if not task:
        return
    await query.message.edit_text(
        _format_task(task, show_solution=True),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Другая задача", callback_data="practice_random")],
            [InlineKeyboardButton("◀️ К выбору уровня", callback_data="practice_menu")],
        ]),
    )

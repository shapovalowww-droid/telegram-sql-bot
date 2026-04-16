import json
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

_FILE = Path(__file__).parent.parent / "data" / "reference.json"


def _load() -> dict:
    with open(_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _ref_list_keyboard() -> InlineKeyboardMarkup:
    ref = _load()
    buttons = []
    keys = list(ref.keys())
    # по 2 кнопки в ряд
    for i in range(0, len(keys), 2):
        row = [InlineKeyboardButton(keys[i], callback_data=f"ref_{keys[i]}")]
        if i + 1 < len(keys):
            row.append(InlineKeyboardButton(keys[i + 1], callback_data=f"ref_{keys[i + 1]}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton("◀️ Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def _back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 К списку команд", callback_data="reference_list")]
    ])


async def cmd_reference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Справочник SQL*\n\nВыбери команду:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_ref_list_keyboard(),
    )


async def show_reference_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text(
        "📖 *Справочник SQL*\n\nВыбери команду:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_ref_list_keyboard(),
    )


async def show_reference_item(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    query = update.callback_query
    ref = _load()
    item = ref.get(key)
    if not item:
        await query.answer("Команда не найдена.")
        return

    text = (
        f"*{key}*\n\n"
        f"📝 {item['description']}\n\n"
        f"*Синтаксис:*\n```sql\n{item['syntax']}\n```\n\n"
        f"*Пример:*\n```sql\n{item['example']}\n```"
    )
    await query.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_back_keyboard(),
    )

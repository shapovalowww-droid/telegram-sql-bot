"""Обработчики Telegram: команды, кнопки меню и свободный диалог с агентом."""
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

import storage.db as db
from agent.claude_agent import run_turn
from agent.prompts import build_system
from keyboards.menus import (
    BTN_ANALYZE,
    BTN_APPLICATIONS,
    BTN_INTERVIEW,
    BTN_PROFILE,
    BTN_RESET,
    BTN_SEARCH,
    MAIN_KB,
)

logger = logging.getLogger(__name__)

WELCOME = (
    "Привет! Я — карьерный ассистент 🤝\n\n"
    "Помогу найти работу: подберу вакансии на hh.ru, разберу конкретную вакансию "
    "под твой профиль и проведу тренировку собеседования.\n\n"
    "Начни с заполнения профиля — так советы будут точнее:\n"
    "/profile Аналитик данных, 3 года опыта, Python/SQL, ищу удалёнку от 200к…\n\n"
    "Или просто напиши, что ищешь, либо выбери действие на клавиатуре ниже."
)

PROFILE_HELP = (
    "Профиль помогает мне подбирать вакансии и советы именно под тебя.\n\n"
    "Чтобы задать или обновить профиль, отправь:\n"
    "/profile <текст>\n\n"
    "Например:\n"
    "/profile Аналитик данных, 3 года опыта, Python/SQL, BI. Ищу удалёнку от 200к, "
    "интересна фрод-аналитика и безопасность.\n\n"
    "Текущий профиль:\n{current}"
)

SEARCH_HINT = (
    "Опиши, какую работу ищешь: должность, город или удалёнка, желаемая зарплата, опыт.\n"
    "Например: «аналитик данных, удалёнка, от 200к, опыт 3 года»."
)

ANALYZE_HINT = (
    "Пришли текст вакансии или ссылку с hh.ru — я разберу требования и оценю, "
    "насколько ты подходишь, что подчеркнуть и какие пробелы закрыть."
)

APPLICATIONS_EMPTY = (
    "В трекере пока пусто 📭\n\n"
    "Найди вакансии (🔍) и попроси сохранить понравившиеся — например «сохрани эту вакансию» "
    "или «я откликнулся на первую». Я буду вести список со статусами."
)


def _format_applications(apps: list) -> str:
    lines = [f"📁 Твои отклики ({len(apps)}):\n"]
    for app in apps:
        status = db.STATUSES.get(app["status"], app["status"])
        head = f"{app['id']}. {app['title']}"
        if app.get("company"):
            head += f" — {app['company']}"
        lines.append(head)
        detail = f"   Статус: {status}"
        if app.get("url"):
            detail += f" · {app['url']}"
        lines.append(detail)
        if app.get("note"):
            lines.append(f"   📝 {app['note']}")
    return "\n".join(lines)


async def show_applications(update: Update, user_id: int) -> None:
    apps = await db.list_applications(user_id)
    if not apps:
        await update.message.reply_text(APPLICATIONS_EMPTY)
        return
    await _reply_long(update, _format_applications(apps))


async def _reply_long(update: Update, text: str) -> None:
    text = text or "Готово."
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i : i + 4000])


async def _run_agent(update: Update, user_id: int, user_text: str) -> None:
    user = await db.get_user(user_id)
    messages = user["history"]
    messages.append({"role": "user", "content": user_text})

    system_text = build_system(user["profile"], user["mode"])
    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        reply, messages = await run_turn(system_text, messages, user_id)
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка агента")
        await update.message.reply_text(
            "Упс, что-то пошло не так при обращении к ИИ. Попробуй ещё раз чуть позже."
        )
        return

    await db.save_history(user_id, db.trim_history(messages))
    await _reply_long(update, reply)


# --- Команды ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await db.get_user(update.effective_user.id)
    await update.message.reply_text(WELCOME, reply_markup=MAIN_KB)


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    profile_text = update.message.text.partition(" ")[2].strip()
    if profile_text:
        await db.set_profile(user_id, profile_text)
        await update.message.reply_text("Профиль сохранён ✅")
    else:
        user = await db.get_user(user_id)
        await update.message.reply_text(PROFILE_HELP.format(current=user["profile"] or "(пусто)"))


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await db.reset_history(update.effective_user.id)
    await update.message.reply_text("Начали новый диалог ♻️", reply_markup=MAIN_KB)


# --- Свободный текст / кнопки ---

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id

    if text == BTN_PROFILE:
        user = await db.get_user(user_id)
        await update.message.reply_text(PROFILE_HELP.format(current=user["profile"] or "(пусто)"))
        return
    if text == BTN_RESET:
        await db.reset_history(user_id)
        await update.message.reply_text("Начали новый диалог ♻️")
        return
    if text == BTN_SEARCH:
        await db.set_mode(user_id, "search")
        await update.message.reply_text(SEARCH_HINT)
        return
    if text == BTN_ANALYZE:
        await db.set_mode(user_id, "analyze")
        await update.message.reply_text(ANALYZE_HINT)
        return
    if text == BTN_APPLICATIONS:
        await show_applications(update, user_id)
        return
    if text == BTN_INTERVIEW:
        await db.set_mode(user_id, "interview")
        await _run_agent(update, user_id, "Начинаем тренировку собеседования.")
        return

    await _run_agent(update, user_id, text)

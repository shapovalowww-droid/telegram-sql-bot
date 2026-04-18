import asyncio
import logging
import re
from datetime import timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from config import BOT_TOKEN, NEWS_INTERVAL_HOURS
from db.database import init_db
from handlers.start import cmd_start
from handlers.news import cmd_news, cmd_subscribe, cmd_unsubscribe, cmd_sources, button_handler as news_button
from handlers.lessons import cmd_lessons, show_lesson, show_answer, show_lessons_list
from handlers.quiz import cmd_quiz, handle_quiz_answer
from handlers.reference import cmd_reference, show_reference_list, show_reference_item
from handlers.practice import (
    cmd_practice, show_practice_menu, show_task_by_level,
    show_random_task, show_hint, show_solution,
)
from keyboards.menus import main_menu
from services.scheduler import broadcast_news


async def show_menu(update: Update, context):
    user = update.effective_user
    from db.models import upsert_user
    await upsert_user(user.id, user.username, user.first_name)
    await update.message.reply_text(
        "Главное меню:",
        reply_markup=main_menu(),
    )

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def callback_router(update: Update, context):
    query = update.callback_query
    data = query.data

    # --- Главное меню ---
    if data == "main_menu":
        await query.answer()
        await query.message.edit_text(
            "Главное меню:",
            reply_markup=main_menu(),
        )

    # --- Уроки ---
    elif data == "lessons_list":
        await query.answer()
        await show_lessons_list(update, context)
    elif re.match(r"^lesson_done_(\d+)$", data):
        lesson_id = int(re.match(r"^lesson_done_(\d+)$", data).group(1))
        await show_answer(update, context, lesson_id)
    elif re.match(r"^lesson_(\d+)$", data):
        lesson_id = int(re.match(r"^lesson_(\d+)$", data).group(1))
        await query.answer()
        await show_lesson(update, context, lesson_id)

    # --- Квиз ---
    elif data == "start_quiz":
        await query.answer()
        await cmd_quiz(update, context)
    elif re.match(r"^quiz_ans_(\w+)_(\d+)_(\d+)$", data):
        m = re.match(r"^quiz_ans_(\w+)_(\d+)_(\d+)$", data)
        session_id, q_index, answer = m.group(1), int(m.group(2)), int(m.group(3))
        await handle_quiz_answer(update, context, session_id, q_index, answer)

    # --- Справочник ---
    elif data == "reference_list":
        await query.answer()
        await show_reference_list(update, context)
    elif data.startswith("ref_"):
        key = data[4:]
        await query.answer()
        await show_reference_item(update, context, key)

    # --- Практика ---
    elif data == "practice_menu":
        await query.answer()
        await show_practice_menu(update, context)
    elif data == "practice_random":
        await query.answer()
        await show_random_task(update, context)
    elif data.startswith("practice_hint_"):
        task_id = int(data.split("_")[-1])
        await query.answer()
        await show_hint(update, context, task_id)
    elif data.startswith("practice_solution_"):
        task_id = int(data.split("_")[-1])
        await query.answer()
        await show_solution(update, context, task_id)
    elif data.startswith("practice_"):
        level = data[len("practice_"):]
        await query.answer()
        await show_task_by_level(update, context, level)

    # --- Новости ---
    else:
        await news_button(update, context)


async def run(app: Application):
    await init_db()
    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Бот запущен. Ожидание сообщений...")
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()


async def error_handler(update: object, context) -> None:
    logger.error("Exception while handling update:", exc_info=context.error)


def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Укажите токен бота в .env: BOT_TOKEN=...")
        return

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("lessons", cmd_lessons))
    app.add_handler(CommandHandler("quiz", cmd_quiz))
    app.add_handler(CommandHandler("practice", cmd_practice))
    app.add_handler(CommandHandler("reference", cmd_reference))
    app.add_handler(CommandHandler("news", cmd_news))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CommandHandler("sources", cmd_sources))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, show_menu))
    app.add_error_handler(error_handler)

    app.job_queue.run_repeating(
        broadcast_news,
        interval=timedelta(hours=NEWS_INTERVAL_HOURS),
        first=timedelta(minutes=1),
    )

    print(f"Бот запущен. Рассылка каждые {NEWS_INTERVAL_HOURS} ч. Ctrl+C для остановки.")
    asyncio.run(run(app))


if __name__ == "__main__":
    main()

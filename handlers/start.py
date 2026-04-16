from telegram import Update
from telegram.ext import ContextTypes
from db.models import upsert_user
from keyboards.menus import main_menu


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)

    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я бот для изучения SQL. Вот что я умею:\n\n"
        "📚 /lessons — уроки по SQL (SELECT, JOIN, транзакции и др.)\n"
        "🧠 /quiz — квиз: проверь свои знания\n"
        "💪 /practice — задачи на практику с решениями\n"
        "📖 /reference — справочник SQL-команд\n"
        "📰 /news — свежие SQL-новости\n"
        "🔔 /subscribe — подписка на авторассылку новостей\n",
        reply_markup=main_menu(),
    )

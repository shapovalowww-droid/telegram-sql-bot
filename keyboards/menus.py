from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📚 Уроки", callback_data="lessons_list"),
            InlineKeyboardButton("🧠 Квиз", callback_data="start_quiz"),
        ],
        [
            InlineKeyboardButton("💪 Практика", callback_data="practice_menu"),
            InlineKeyboardButton("📖 Справочник", callback_data="reference_list"),
        ],
        [
            InlineKeyboardButton("📰 SQL-новости", callback_data="news_latest"),
            InlineKeyboardButton("🔔 Подписаться", callback_data="news_subscribe"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

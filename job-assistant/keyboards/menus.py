from telegram import ReplyKeyboardMarkup

BTN_SEARCH = "🔍 Поиск вакансий"
BTN_ANALYZE = "📋 Разбор вакансии"
BTN_INTERVIEW = "🎤 Собеседование"
BTN_PROFILE = "👤 Профиль"
BTN_RESET = "♻️ Новый диалог"

MAIN_KB = ReplyKeyboardMarkup(
    [
        [BTN_SEARCH, BTN_ANALYZE],
        [BTN_INTERVIEW],
        [BTN_PROFILE, BTN_RESET],
    ],
    resize_keyboard=True,
)

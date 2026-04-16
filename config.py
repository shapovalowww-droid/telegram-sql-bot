import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# Настройки новостей
NEWS_INTERVAL_HOURS: int = int(os.getenv("NEWS_INTERVAL_HOURS", "4"))
NEWS_PER_SOURCE: int = int(os.getenv("NEWS_PER_SOURCE", "2"))

# Пути к файлам
DB_PATH: str = os.getenv("DB_PATH", "db/sql_bot.db")

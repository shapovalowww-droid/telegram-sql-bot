import os

from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# Anthropic / Claude
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
# low | medium | high | max  (medium — баланс скорости и качества для чат-бота)
ANTHROPIC_EFFORT: str = os.getenv("ANTHROPIC_EFFORT", "medium")
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "6000"))

# Сколько раундов tool-use разрешаем за один ход пользователя
MAX_TOOL_ITERATIONS: int = int(os.getenv("MAX_TOOL_ITERATIONS", "6"))

# Сколько последних сообщений диалога храним (контроль контекста/стоимости)
MAX_HISTORY_MESSAGES: int = int(os.getenv("MAX_HISTORY_MESSAGES", "40"))

# Хранилище
DB_PATH: str = os.getenv("DB_PATH", "job_assistant.db")

# hh.ru требует осмысленный User-Agent
HH_USER_AGENT: str = os.getenv("HH_USER_AGENT", "JobAssistantBot/1.0 (telegram career assistant)")

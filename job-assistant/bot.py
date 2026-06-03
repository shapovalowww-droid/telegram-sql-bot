"""Точка входа: карьерный ИИ-ассистент в Telegram на Claude."""
import logging

from telegram.ext import Application, CommandHandler, MessageHandler, filters

import config
import handlers.telegram_handlers as h
import storage.db as db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


async def _post_init(app: Application) -> None:
    await db.init_db()


def main() -> None:
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN не задан — заполни .env (см. .env.example)")
    if not config.ANTHROPIC_API_KEY:
        raise SystemExit("ANTHROPIC_API_KEY не задан — заполни .env (см. .env.example)")

    app = Application.builder().token(config.BOT_TOKEN).post_init(_post_init).build()

    app.add_handler(CommandHandler("start", h.start))
    app.add_handler(CommandHandler("profile", h.cmd_profile))
    app.add_handler(CommandHandler("reset", h.cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, h.on_message))

    app.run_polling()


if __name__ == "__main__":
    main()

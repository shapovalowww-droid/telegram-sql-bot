import asyncio
import logging
from datetime import datetime
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from db.models import get_subscribers, unsubscribe
from services.news_fetcher import fetch_news, format_article

logger = logging.getLogger(__name__)


async def broadcast_news(context: ContextTypes.DEFAULT_TYPE):
    subscribers = await get_subscribers()
    if not subscribers:
        logger.info("Нет подписчиков для рассылки.")
        return

    articles = await fetch_news()
    if not articles:
        logger.info("Нет новых статей для рассылки.")
        return

    logger.info(f"Рассылка {len(articles)} статей для {len(subscribers)} подписчиков")

    for chat_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🗞 *SQL-новости* ({datetime.now().strftime('%H:%M %d.%m')})",
                parse_mode=ParseMode.MARKDOWN,
            )
            for article in articles:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=format_article(article),
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_web_page_preview=False,
                    )
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.error(f"Ошибка отправки статьи в {chat_id}: {e}")
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Ошибка рассылки в {chat_id}: {e}")
            if "blocked" in str(e).lower() or "chat not found" in str(e).lower():
                await unsubscribe(chat_id)
                logger.info(f"Пользователь {chat_id} удалён из подписчиков.")

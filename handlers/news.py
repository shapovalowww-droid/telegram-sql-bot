import asyncio
import json
import logging
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from db.models import subscribe, unsubscribe, is_subscribed, upsert_user
from services.news_fetcher import fetch_news, format_article
from keyboards.menus import main_menu

logger = logging.getLogger(__name__)
_SOURCES_FILE = Path(__file__).parent.parent / "data" / "rss_sources.json"


async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)

    msg = await update.message.reply_text("⏳ Загружаю свежие SQL-новости...")
    articles = await fetch_news()

    if not articles:
        await msg.edit_text(
            "😔 Свежих новостей пока нет — все уже были отправлены.\n"
            "Попробуй позже.",
            reply_markup=main_menu(),
        )
        return

    await msg.edit_text(f"✅ Найдено статей: {len(articles)}")

    for article in articles:
        try:
            await update.message.reply_text(
                format_article(article),
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=False,
            )
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.error(f"Ошибка отправки статьи: {e}")


async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await upsert_user(user.id, user.username, user.first_name)

    if await is_subscribed(user.id):
        await update.message.reply_text(
            "✅ Вы уже подписаны на SQL-новости.\n"
            "Отписаться: /unsubscribe",
            reply_markup=main_menu(),
        )
        return

    await subscribe(user.id)
    from config import NEWS_INTERVAL_HOURS
    await update.message.reply_text(
        f"🔔 Подписка оформлена!\n"
        f"Буду присылать SQL-новости каждые {NEWS_INTERVAL_HOURS} ч.\n\n"
        "Отписаться: /unsubscribe",
        reply_markup=main_menu(),
    )


async def cmd_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not await is_subscribed(user.id):
        await update.message.reply_text(
            "Вы не были подписаны на рассылку.",
            reply_markup=main_menu(),
        )
        return

    await unsubscribe(user.id)
    await update.message.reply_text(
        "🔕 Вы отписались от рассылки SQL-новостей.\n"
        "Снова подписаться: /subscribe",
        reply_markup=main_menu(),
    )


async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(_SOURCES_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)

    lines = ["📡 *Источники SQL-новостей:*\n"]
    for name, url in sources.items():
        lines.append(f"• [{name}]({url})")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


# --- Обработчик inline-кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == "news_latest":
        await query.message.reply_text("⏳ Загружаю свежие SQL-новости...")
        articles = await fetch_news()
        if not articles:
            await query.message.reply_text(
                "😔 Свежих новостей пока нет. Попробуй позже.",
                reply_markup=main_menu(),
            )
            return
        await query.message.reply_text(f"✅ Найдено статей: {len(articles)}")
        for article in articles:
            try:
                await query.message.reply_text(
                    format_article(article),
                    parse_mode=ParseMode.MARKDOWN_V2,
                    disable_web_page_preview=False,
                )
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"Ошибка: {e}")

    elif query.data == "news_subscribe":
        await upsert_user(user.id, user.username, user.first_name)
        if await is_subscribed(user.id):
            await query.message.reply_text("✅ Вы уже подписаны! Отписаться: /unsubscribe")
        else:
            await subscribe(user.id)
            from config import NEWS_INTERVAL_HOURS
            await query.message.reply_text(
                f"🔔 Подписка оформлена! Новости каждые {NEWS_INTERVAL_HOURS} ч.\n"
                "Отписаться: /unsubscribe"
            )

    elif query.data == "news_unsubscribe":
        if await is_subscribed(user.id):
            await unsubscribe(user.id)
            await query.message.reply_text("🔕 Вы отписались от рассылки.")
        else:
            await query.message.reply_text("Вы не были подписаны.")

    elif query.data == "news_sources":
        with open(_SOURCES_FILE, "r", encoding="utf-8") as f:
            sources = json.load(f)
        lines = ["📡 *Источники SQL-новостей:*\n"]
        for name, url in sources.items():
            lines.append(f"• [{name}]({url})")
        await query.message.reply_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )

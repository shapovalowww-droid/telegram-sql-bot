import html
import json
import logging
import requests
import urllib3
import feedparser
from pathlib import Path
from db.models import is_news_sent, mark_news_sent
from services.translator import translate_to_russian
from config import NEWS_PER_SOURCE

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

_SOURCES_FILE = Path(__file__).parent.parent / "data" / "rss_sources.json"


def _load_sources() -> dict[str, str]:
    with open(_SOURCES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _clean(text: str, limit: int = 250) -> str:
    text = html.unescape(text).strip()
    # убираем HTML-теги
    import re
    text = re.sub(r"<[^>]+>", "", text)
    if len(text) > limit:
        text = text[:limit].rstrip() + "..."
    return text


async def fetch_news(max_per_source: int = NEWS_PER_SOURCE) -> list[dict]:
    sources = _load_sources()
    articles = []

    for source_name, url in sources.items():
        try:
            response = requests.get(
                url,
                timeout=10,
                verify=False,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            feed = feedparser.parse(response.content)
            count = 0

            for entry in feed.entries:
                if count >= max_per_source:
                    break

                link = entry.get("link", "").strip()
                if not link:
                    continue
                if await is_news_sent(link):
                    continue

                raw_title = _clean(entry.get("title", "Без заголовка"), limit=200)
                raw_summary = _clean(entry.get("summary", ""), limit=300)

                title = translate_to_russian(raw_title)
                summary = translate_to_russian(raw_summary) if raw_summary else ""

                articles.append({
                    "source": source_name,
                    "title": title,
                    "link": link,
                    "summary": summary,
                })
                count += 1

        except Exception as e:
            logger.error(f"Ошибка парсинга {source_name}: {e}")

    if articles:
        await mark_news_sent([a["link"] for a in articles])

    return articles


def escape_md(text: str) -> str:
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))


def format_article(article: dict) -> str:
    lines = [
        f"📰 *{escape_md(article['source'])}*",
        f"[{escape_md(article['title'])}]({article['link']})",
    ]
    if article.get("summary"):
        lines.append(f"_{escape_md(article['summary'])}_")
    return "\n".join(lines)

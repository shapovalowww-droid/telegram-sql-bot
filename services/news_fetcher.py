import asyncio
import html
import json
import logging
import re
from pathlib import Path

import aiohttp
import feedparser

from config import NEWS_PER_SOURCE
from db.models import get_sent_urls, mark_news_sent
from services.translator import translate_to_russian

logger = logging.getLogger(__name__)

_SOURCES_FILE = Path(__file__).parent.parent / "data" / "rss_sources.json"


def _load_sources() -> dict[str, str]:
    with open(_SOURCES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _clean(text: str, limit: int = 250) -> str:
    text = html.unescape(text).strip()
    text = re.sub(r"<[^>]+>", "", text)
    if len(text) > limit:
        text = text[:limit].rstrip() + "..."
    return text


async def _fetch_source(
    session: aiohttp.ClientSession,
    source_name: str,
    url: str,
    max_per_source: int,
) -> list[dict]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            content = await resp.read()
        feed = feedparser.parse(content)
        candidates = []
        for entry in feed.entries[:max_per_source * 3]:
            link = entry.get("link", "").strip()
            if not link:
                continue
            candidates.append({
                "source": source_name,
                "link": link,
                "raw_title": _clean(entry.get("title", "Без заголовка"), limit=200),
                "raw_summary": _clean(entry.get("summary", ""), limit=300),
            })
        return candidates
    except Exception as e:
        logger.error(f"Ошибка парсинга {source_name}: {e}")
        return []


async def fetch_news(max_per_source: int = NEWS_PER_SOURCE) -> list[dict]:
    sources = _load_sources()
    loop = asyncio.get_event_loop()

    connector = aiohttp.TCPConnector(ssl=False)
    headers = {"User-Agent": "Mozilla/5.0"}

    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        results = await asyncio.gather(
            *[_fetch_source(session, name, url, max_per_source) for name, url in sources.items()]
        )

    all_candidates: list[dict] = []
    for source_candidates in results:
        all_candidates.extend(source_candidates)

    all_links = [c["link"] for c in all_candidates]
    already_sent = await get_sent_urls(all_links)

    per_source_count: dict[str, int] = {}
    new_candidates = []
    for c in all_candidates:
        if c["link"] in already_sent:
            continue
        count = per_source_count.get(c["source"], 0)
        if count >= max_per_source:
            continue
        per_source_count[c["source"]] = count + 1
        new_candidates.append(c)

    if not new_candidates:
        return []

    async def translate(text: str) -> str:
        if not text:
            return text
        return await loop.run_in_executor(None, translate_to_russian, text)

    translate_tasks = []
    for c in new_candidates:
        translate_tasks.append(translate(c["raw_title"]))
        translate_tasks.append(translate(c["raw_summary"]))

    translated = await asyncio.gather(*translate_tasks)

    articles = []
    for i, c in enumerate(new_candidates):
        articles.append({
            "source": c["source"],
            "title": translated[i * 2],
            "link": c["link"],
            "summary": translated[i * 2 + 1],
        })

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

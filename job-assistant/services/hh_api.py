"""Асинхронный клиент к открытому API HeadHunter (hh.ru).

Документация: https://api.hh.ru/openapi/redoc
Аутентификация для поиска вакансий не требуется, нужен только User-Agent.
"""
import re

import aiohttp

import config

HH_BASE = "https://api.hh.ru"
_HEADERS = {"User-Agent": config.HH_USER_AGENT}


async def _get(session: aiohttp.ClientSession, path: str, params: dict) -> dict:
    async with session.get(f"{HH_BASE}{path}", params=params, headers=_HEADERS) as resp:
        resp.raise_for_status()
        return await resp.json()


def _salary_str(salary: dict | None) -> str:
    if not salary:
        return "не указана"
    fr, to, cur = salary.get("from"), salary.get("to"), salary.get("currency") or ""
    if fr and to:
        return f"{fr}–{to} {cur}"
    if fr:
        return f"от {fr} {cur}"
    if to:
        return f"до {to} {cur}"
    return "не указана"


def _strip_html(html: str | None) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:4000]


def _extract_id(value) -> str:
    """Достаёт числовой id вакансии из строки или ссылки hh.ru."""
    m = re.search(r"(\d{6,})", str(value))
    return m.group(1) if m else str(value)


def _format_item(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "employer": (item.get("employer") or {}).get("name"),
        "area": (item.get("area") or {}).get("name"),
        "salary": _salary_str(item.get("salary")),
        "url": item.get("alternate_url"),
        "snippet": _strip_html(
            ((item.get("snippet") or {}).get("requirement") or "")
            + " "
            + ((item.get("snippet") or {}).get("responsibility") or "")
        ),
    }


async def _resolve_area(session: aiohttp.ClientSession, name: str) -> str | None:
    if not name:
        return None
    data = await _get(session, "/suggests/areas", {"text": name})
    items = data.get("items", [])
    return items[0]["id"] if items else None


async def search_vacancies(
    text: str,
    area: str | None = None,
    salary: int | None = None,
    experience: str | None = None,
    schedule: str | None = None,
    employment: str | None = None,
    per_page: int = 5,
) -> list[dict]:
    """Поиск вакансий. Возвращает список кратких карточек."""
    async with aiohttp.ClientSession() as session:
        params: dict = {
            "text": text,
            "per_page": max(1, min(int(per_page or 5), 10)),
            "order_by": "relevance",
        }
        if area:
            area_id = await _resolve_area(session, area)
            if area_id:
                params["area"] = area_id
        if salary:
            params["salary"] = int(salary)
        if experience:
            params["experience"] = experience
        if schedule:
            params["schedule"] = schedule
        if employment:
            params["employment"] = employment

        data = await _get(session, "/vacancies", params)
        return [_format_item(i) for i in data.get("items", [])]


async def get_vacancy_details(vacancy_id) -> dict:
    """Полное описание одной вакансии по id (или ссылке hh.ru)."""
    vid = _extract_id(vacancy_id)
    async with aiohttp.ClientSession() as session:
        data = await _get(session, f"/vacancies/{vid}", {})
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "employer": (data.get("employer") or {}).get("name"),
        "area": (data.get("area") or {}).get("name"),
        "salary": _salary_str(data.get("salary")),
        "experience": (data.get("experience") or {}).get("name"),
        "employment": (data.get("employment") or {}).get("name"),
        "schedule": (data.get("schedule") or {}).get("name"),
        "key_skills": [k["name"] for k in data.get("key_skills", [])],
        "description": _strip_html(data.get("description", "")),
        "url": data.get("alternate_url"),
    }

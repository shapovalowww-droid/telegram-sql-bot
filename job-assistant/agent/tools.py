"""Определения инструментов (function calling) и их исполнение."""
import json
import logging

from services import hh_api

logger = logging.getLogger(__name__)

TOOLS = [
    {
        "name": "search_vacancies",
        "description": (
            "Поиск актуальных вакансий на hh.ru. Вызывай, когда пользователь просит найти, "
            "подобрать или показать вакансии. Перед вызовом убедись, что знаешь хотя бы должность; "
            "город, зарплату и опыт уточняй у пользователя, если это важно, но не задавай "
            "слишком много вопросов сразу."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Ключевые слова или должность, например 'аналитик данных' или 'python developer'.",
                },
                "area": {
                    "type": "string",
                    "description": "Город или регион (например 'Москва', 'Санкт-Петербург'). Опусти для поиска по всей России.",
                },
                "salary": {
                    "type": "integer",
                    "description": "Желаемая зарплата в рублях (нижняя граница).",
                },
                "experience": {
                    "type": "string",
                    "enum": ["noExperience", "between1And3", "between3And6", "moreThan6"],
                    "description": "Опыт: noExperience — нет опыта, between1And3 — 1–3 года, between3And6 — 3–6 лет, moreThan6 — более 6 лет.",
                },
                "schedule": {
                    "type": "string",
                    "enum": ["remote", "fullDay", "flexible", "shift"],
                    "description": "График: remote — удалёнка, fullDay — полный день, flexible — гибкий, shift — сменный.",
                },
                "employment": {
                    "type": "string",
                    "enum": ["full", "part", "project", "probation"],
                    "description": "Занятость: full — полная, part — частичная, project — проект, probation — стажировка.",
                },
                "per_page": {
                    "type": "integer",
                    "description": "Сколько вакансий вернуть (1–10), по умолчанию 5.",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "get_vacancy_details",
        "description": (
            "Получить полное описание одной вакансии: требования, ключевые навыки, условия. "
            "Вызывай, когда нужно детально разобрать конкретную вакансию. В vacancy_id можно "
            "передать как числовой id из результатов search_vacancies, так и ссылку hh.ru — "
            "id будет извлечён автоматически."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "vacancy_id": {
                    "type": "string",
                    "description": "id вакансии или ссылка hh.ru (например https://hh.ru/vacancy/12345678).",
                }
            },
            "required": ["vacancy_id"],
        },
    },
]

_SEARCH_KEYS = {"text", "area", "salary", "experience", "schedule", "employment", "per_page"}


async def dispatch(name: str, tool_input: dict) -> str:
    """Исполняет инструмент и возвращает строку (JSON) для модели."""
    try:
        if name == "search_vacancies":
            args = {k: v for k, v in (tool_input or {}).items() if k in _SEARCH_KEYS and v not in (None, "")}
            items = await hh_api.search_vacancies(**args)
            if not items:
                return "По заданным критериям вакансии не найдены. Предложи пользователю смягчить фильтры (зарплата, город, опыт)."
            return json.dumps(items, ensure_ascii=False)

        if name == "get_vacancy_details":
            details = await hh_api.get_vacancy_details(tool_input["vacancy_id"])
            return json.dumps(details, ensure_ascii=False)

        return f"Неизвестный инструмент: {name}"
    except Exception as exc:  # noqa: BLE001 — отдаём ошибку модели, она объяснит пользователю
        logger.exception("Ошибка инструмента %s", name)
        return f"Ошибка при обращении к hh.ru: {exc}"

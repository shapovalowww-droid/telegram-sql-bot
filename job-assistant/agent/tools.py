"""Определения инструментов (function calling) и их исполнение."""
import json
import logging

import storage.db as db
from services import hh_api

logger = logging.getLogger(__name__)

_STATUS_ENUM = list(db.STATUSES.keys())
_STATUS_DESC = ", ".join(f"{code} — {label}" for code, label in db.STATUSES.items())

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
    {
        "name": "save_application",
        "description": (
            "Сохранить вакансию в трекер откликов пользователя. Вызывай, когда пользователь "
            "просит сохранить/добавить вакансию или говорит, что откликнулся на неё. "
            "Бери данные (должность, компания, ссылка) из результатов поиска или из текста пользователя."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Должность/название вакансии."},
                "company": {"type": "string", "description": "Компания (работодатель)."},
                "url": {"type": "string", "description": "Ссылка на вакансию (hh.ru)."},
                "status": {
                    "type": "string",
                    "enum": _STATUS_ENUM,
                    "description": f"Статус отклика: {_STATUS_DESC}. По умолчанию saved.",
                },
                "note": {"type": "string", "description": "Заметка пользователя (необязательно)."},
            },
            "required": ["title"],
        },
    },
    {
        "name": "list_applications",
        "description": (
            "Показать все отклики пользователя из трекера со статусами. Вызывай, когда пользователь "
            "просит показать свои отклики/сохранённые вакансии или спрашивает про их статус. "
            "Используй id из результата, чтобы обновлять статусы через update_application."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "update_application",
        "description": (
            "Обновить статус или заметку существующего отклика. Вызывай, когда пользователь сообщает "
            "об изменении (пригласили на собес, получил оффер/отказ и т.п.). "
            "application_id бери из list_applications."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "application_id": {"type": "integer", "description": "id отклика из трекера."},
                "status": {
                    "type": "string",
                    "enum": _STATUS_ENUM,
                    "description": f"Новый статус: {_STATUS_DESC}.",
                },
                "note": {"type": "string", "description": "Новая заметка (необязательно)."},
            },
            "required": ["application_id"],
        },
    },
]

_SEARCH_KEYS = {"text", "area", "salary", "experience", "schedule", "employment", "per_page"}


async def dispatch(name: str, tool_input: dict, user_id: int) -> str:
    """Исполняет инструмент и возвращает строку (JSON) для модели."""
    tool_input = tool_input or {}
    try:
        if name == "search_vacancies":
            args = {k: v for k, v in tool_input.items() if k in _SEARCH_KEYS and v not in (None, "")}
            items = await hh_api.search_vacancies(**args)
            if not items:
                return "По заданным критериям вакансии не найдены. Предложи пользователю смягчить фильтры (зарплата, город, опыт)."
            return json.dumps(items, ensure_ascii=False)

        if name == "get_vacancy_details":
            details = await hh_api.get_vacancy_details(tool_input["vacancy_id"])
            return json.dumps(details, ensure_ascii=False)

        if name == "save_application":
            app_id = await db.add_application(
                user_id,
                title=tool_input["title"],
                company=tool_input.get("company", ""),
                url=tool_input.get("url", ""),
                status=tool_input.get("status", "saved"),
                note=tool_input.get("note", ""),
            )
            return json.dumps({"ok": True, "application_id": app_id}, ensure_ascii=False)

        if name == "list_applications":
            apps = await db.list_applications(user_id)
            if not apps:
                return "Трекер пуст. Предложи сохранить понравившиеся вакансии."
            return json.dumps(apps, ensure_ascii=False)

        if name == "update_application":
            ok = await db.update_application(
                user_id,
                application_id=tool_input["application_id"],
                status=tool_input.get("status"),
                note=tool_input.get("note"),
            )
            if not ok:
                return "Не удалось обновить: отклик с таким id не найден или не передан статус/заметка."
            return json.dumps({"ok": True}, ensure_ascii=False)

        return f"Неизвестный инструмент: {name}"
    except Exception as exc:  # noqa: BLE001 — отдаём ошибку модели, она объяснит пользователю
        logger.exception("Ошибка инструмента %s", name)
        return f"Ошибка при выполнении инструмента: {exc}"

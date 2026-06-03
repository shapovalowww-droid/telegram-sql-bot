"""Агентный цикл на Claude: tool use + мультитёрн + prompt caching."""
import logging

from anthropic import AsyncAnthropic

import config
from agent.tools import TOOLS, dispatch

logger = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def _blocks_to_dicts(content) -> list:
    """Преобразует content-блоки ответа в JSON-совместимые dict для истории.

    Важно сохранять блоки thinking (с подписью) и tool_use целиком — они нужны
    модели на последующих ходах при включённом adaptive thinking и tool use.
    """
    out = []
    for block in content:
        if hasattr(block, "model_dump"):
            out.append(block.model_dump(exclude_none=True))
        else:
            out.append(block)
    return out


def _extract_text(response) -> str:
    parts = [b.text for b in response.content if getattr(b, "type", None) == "text" and getattr(b, "text", None)]
    return "\n".join(parts).strip()


async def run_turn(system_text: str, messages: list) -> tuple[str, list]:
    """Прогоняет один ход пользователя через агентный цикл.

    Возвращает (текст ответа, обновлённый список messages).
    `messages` мутируется и возвращается, чтобы вызывающий код сохранил историю.
    """
    client = _get_client()
    # Системный промпт кешируется: основной объём токенов (инструкции + профиль),
    # стабильный в пределах сессии пользователя.
    system = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]

    response = None
    for _ in range(config.MAX_TOOL_ITERATIONS):
        response = await client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=config.MAX_TOKENS,
            system=system,
            messages=messages,
            tools=TOOLS,
            thinking={"type": "adaptive"},
            output_config={"effort": config.ANTHROPIC_EFFORT},
        )

        messages.append({"role": "assistant", "content": _blocks_to_dicts(response.content)})

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                result = await dispatch(block.name, block.input)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                )
        messages.append({"role": "user", "content": tool_results})

    text = _extract_text(response) if response is not None else ""
    if not text:
        text = "Не удалось сформировать ответ. Попробуй переформулировать запрос."
    return text, messages

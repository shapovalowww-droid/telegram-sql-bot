import logging
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)


def is_russian(text: str) -> bool:
    try:
        return detect(text) == "ru"
    except LangDetectException:
        return False


def translate_to_russian(text: str) -> str:
    if not text or is_russian(text):
        return text
    try:
        return GoogleTranslator(source="auto", target="ru").translate(text)
    except Exception as e:
        logger.warning(f"Ошибка перевода: {e}")
        return text

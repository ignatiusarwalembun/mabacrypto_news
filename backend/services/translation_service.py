from functools import lru_cache

from deep_translator import GoogleTranslator
from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0


def is_english(text: str) -> bool:
    sample = (text or "").strip()
    if len(sample) < 12:
        return False
    try:
        return detect(sample) == "en"
    except LangDetectException:
        return False


@lru_cache(maxsize=1024)
def _translate_cached(text: str) -> str:
    return GoogleTranslator(source="auto", target="id").translate(text)


def translate_to_indonesian(title: str, summary: str) -> tuple[str, str, bool]:
    combined = f"{title}. {summary}".strip()
    if not is_english(combined):
        return title, summary, False

    try:
        translated_title = _translate_cached(title) if title else title
        translated_summary = _translate_cached(summary) if summary else summary
        return translated_title or title, translated_summary or summary, True
    except Exception:
        return title, summary, False

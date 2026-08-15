import logging
import os
import queue
import threading
from functools import lru_cache

logger = logging.getLogger(__name__)
_translation_queue = queue.Queue(maxsize=500)
_worker_started = False
_worker_lock = threading.Lock()


def _enabled() -> bool:
    return os.getenv("TRANSLATION_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}


@lru_cache(maxsize=1024)
def translate_to_indonesian(text: str) -> str:
    """Translate English text with a free library-backed translator.

    It uses no API key and no LLM API. Any failure returns the original text.
    """
    if not text or not _enabled():
        return text
    try:
        from deep_translator import GoogleTranslator

        value = text.strip()[:4500]
        translated = GoogleTranslator(source="en", target="id").translate(value)
        return translated.strip() if translated else text
    except Exception as exc:
        logger.warning("Translation failed; using original text: %s", exc)
        return text


def detect_language(text: str) -> str:
    if not text:
        return "unknown"
    try:
        from langdetect import DetectorFactory, detect

        DetectorFactory.seed = 0
        return detect(text)
    except Exception:
        lowered = f" {text.lower()} "
        id_markers = [" yang ", " dan ", " untuk ", " dari ", " dengan ", " pada ", " ini ", " akan "]
        return "id" if sum(marker in lowered for marker in id_markers) >= 2 else "unknown"


def _translation_worker():
    from services.database import update_translation

    while True:
        fingerprint, title, summary = _translation_queue.get()
        try:
            title_id = translate_to_indonesian(title)
            summary_id = translate_to_indonesian(summary)
            update_translation(
                fingerprint,
                title_id if title_id != title else None,
                summary_id if summary_id != summary else None,
            )
        except Exception:
            logger.exception("Background translation failed; original article remains available")
        finally:
            _translation_queue.task_done()


def _start_worker_safely():
    global _worker_started
    if not _enabled() or _worker_started:
        return
    with _worker_lock:
        if _worker_started:
            return
        try:
            threading.Thread(target=_translation_worker, name="news-translation", daemon=True).start()
            _worker_started = True
        except Exception:
            logger.exception("Translation worker could not start; original text will be used")


def queue_translation(fingerprint: str, title: str, summary: str) -> None:
    if not _enabled():
        return
    _start_worker_safely()
    try:
        _translation_queue.put_nowait((fingerprint, title, summary))
    except queue.Full:
        logger.warning("Translation queue full; keeping original text for this article")

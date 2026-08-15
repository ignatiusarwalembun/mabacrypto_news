import logging
import os
import threading
import time


logger = logging.getLogger(__name__)
_started = False
_lock = threading.Lock()


def _minutes() -> int:
    try:
        return max(1, int(os.getenv("NEWS_REFRESH_MINUTES", "20")))
    except ValueError:
        return 20


def _enabled() -> bool:
    return os.getenv("ENABLE_SCHEDULER", "true").strip().lower() not in {"0", "false", "no", "off"}


def _worker():
    # Let the web server become healthy first. Refresh work is never part of startup health.
    time.sleep(5)
    while True:
        try:
            from services.feeds import refresh_news
            refresh_news()
        except Exception:
            logger.exception("Background news refresh failed; API remains online")
        time.sleep(_minutes() * 60)


def start_scheduler_safely() -> None:
    global _started
    if not _enabled():
        logger.info("Background scheduler disabled")
        return
    with _lock:
        if _started:
            return
        try:
            thread = threading.Thread(target=_worker, name="news-refresh", daemon=True)
            thread.start()
            _started = True
            logger.info("Background scheduler started (%s minutes)", _minutes())
        except Exception:
            logger.exception("Scheduler could not start; API will continue without it")

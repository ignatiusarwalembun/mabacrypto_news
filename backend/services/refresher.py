import threading
from datetime import datetime, timezone

from .analyzer import analyze_batch
from .database import existing_ids, upsert_news
from .news_collector import collect_news

_lock = threading.Lock()
_state = {
    "running": False,
    "last_started_at": None,
    "last_finished_at": None,
    "last_count": 0,
    "last_new_count": 0,
    "last_error": None,
}


def refresh_news():
    if not _lock.acquire(blocking=False):
        return {**_state, "message": "Refresh already running"}
    try:
        _state.update({
            "running": True,
            "last_started_at": datetime.now(timezone.utc).isoformat(),
            "last_error": None,
        })
        items = collect_news()
        known = existing_ids([item["id"] for item in items])
        new_items = [item for item in items if item["id"] not in known]

        analyzed = analyze_batch(new_items)
        for item in analyzed:
            upsert_news(item)

        _state.update({
            "last_count": len(items),
            "last_new_count": len(analyzed),
            "last_finished_at": datetime.now(timezone.utc).isoformat(),
        })
        return dict(_state)
    except Exception as exc:
        _state["last_error"] = f"{type(exc).__name__}: {exc}"
        return dict(_state)
    finally:
        _state["running"] = False
        _lock.release()


def get_refresh_state():
    return dict(_state)


def refresh_news_async():
    """Start a refresh in the background and return immediately."""
    if _state.get("running"):
        return {**_state, "message": "Refresh already running"}

    thread = threading.Thread(
        target=refresh_news,
        name="mabacrypto-news-refresh",
        daemon=True,
    )
    thread.start()
    return {**_state, "message": "Refresh started in background"}

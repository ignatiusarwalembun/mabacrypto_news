from flask import Blueprint, jsonify, request

from services.database import count_news, query_news, set_saved, stats
from services.refresher import get_refresh_state, refresh_news, refresh_news_async

news_bp = Blueprint("news", __name__, url_prefix="/api")


@news_bp.get("/health")
def health():
    return jsonify({"ok": True, "service": "Golden News Intelligence API"})


@news_bp.get("/news")
def news():
    # Never block the first API request while external feeds are fetched.
    # If the DB is empty, kick off a background refresh and immediately
    # return the current (possibly empty) dataset.
    if count_news() == 0:
        refresh_news_async()

    category = request.args.get("category", "all")
    source = request.args.get("source", "all")
    important = request.args.get("important", "false").lower() == "true"
    saved = request.args.get("saved", "false").lower() == "true"
    search = request.args.get("search", "").strip() or None
    limit = request.args.get("limit", 80)

    data = query_news(
        category=category,
        source=source,
        important=important,
        saved=saved,
        search=search,
        limit=limit,
    )
    return jsonify({"items": data, "count": len(data), "stats": stats(), "refresh": get_refresh_state()})


@news_bp.post("/refresh")
def refresh():
    return jsonify(refresh_news())


@news_bp.patch("/news/<news_id>/saved")
def save(news_id):
    payload = request.get_json(silent=True) or {}
    is_saved = bool(payload.get("is_saved", True))
    if not set_saved(news_id, is_saved):
        return jsonify({"ok": False, "error": "News not found"}), 404
    return jsonify({"ok": True, "id": news_id, "is_saved": is_saved})

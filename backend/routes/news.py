from flask import Blueprint, jsonify, request

from database import get_stats, list_news, update_saved
from services.news_service import get_refresh_state, refresh_news

news_bp = Blueprint("news", __name__)


def parse_bool(value):
    if value is None:
        return None
    return str(value).lower() in {"1", "true", "yes", "on"}


@news_bp.get("/news")
def get_news():
    items = list_news(
        category=request.args.get("category") or None,
        source=request.args.get("source") or None,
        saved=parse_bool(request.args.get("saved")),
        important=parse_bool(request.args.get("important")),
        search=(request.args.get("search") or "").strip() or None,
        limit=request.args.get("limit", default=250, type=int) or 250,
    )
    for item in items:
        item["saved"] = bool(item["saved"])
        item["translated"] = bool(item["translated"])
    return jsonify(
        {
            "ok": True,
            "news": items,
            "stats": get_stats(),
            "refresh": get_refresh_state(),
        }
    )


@news_bp.post("/refresh")
def refresh():
    result = refresh_news()
    status = 200 if result.get("ok", False) or result.get("already_running") else 502
    return jsonify(result), status


@news_bp.patch("/news/<int:news_id>/saved")
def patch_saved(news_id: int):
    body = request.get_json(silent=True) or {}
    if "saved" not in body or not isinstance(body["saved"], bool):
        return jsonify({"ok": False, "error": "Field 'saved' harus boolean."}), 400

    item = update_saved(news_id, body["saved"])
    if item is None:
        return jsonify({"ok": False, "error": "Berita tidak ditemukan."}), 404

    item["saved"] = bool(item["saved"])
    item["translated"] = bool(item["translated"])
    return jsonify({"ok": True, "news": item})

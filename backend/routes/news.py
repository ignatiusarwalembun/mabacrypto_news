import json
from flask import Blueprint, jsonify, request

from services.database import delete_expired_news, get_state, news_stats, query_news, set_saved

news_bp = Blueprint("news", __name__)

VALID_CATEGORIES = {"Investment", "Technology", "Blockchain & Crypto"}
VALID_SOURCES = {"BLOOMBERG", "GOOGLE NEWS"}


def serialize_row(row):
    return {
        "id": row["id"],
        "title": row["title_id"] or row["title_original"],
        "summary": row["summary_id"] or row["summary_original"],
        "title_original": row["title_original"],
        "summary_original": row["summary_original"],
        "translated": bool(row["title_id"] or row["summary_id"]),
        "language": row["language"],
        "publisher": row["publisher"],
        "source": row["source"],
        "category": row["category"],
        "published_at": row["published_at"],
        "original_url": row["original_url"],
        "importance_score": row["importance_score"],
        "importance_level": row["importance_level"],
        "saved": bool(row["saved"]),
    }


def refresh_state():
    state = get_state("last_refresh")
    if not state:
        return None
    try:
        data = json.loads(state["value"])
        if isinstance(data.get("sources"), dict):
            data["sources"] = {
                key: value for key, value in data["sources"].items() if key in VALID_SOURCES
            }
            data["partial_failure"] = any(
                isinstance(value, dict) and value.get("ok") is False
                for value in data["sources"].values()
            )
        data["state_updated_at"] = state["updated_at"]
        return data
    except Exception:
        return None


@news_bp.get("/news")
def get_news():
    category = request.args.get("category", "").strip() or None
    source = request.args.get("source", "").strip().upper() or None
    important = request.args.get("important", "").lower() in {"1", "true", "yes"}
    saved = request.args.get("saved", "").lower() in {"1", "true", "yes"}

    if category and category not in VALID_CATEGORIES:
        return jsonify({"ok": False, "error": "Kategori tidak valid."}), 400
    if source and source not in VALID_SOURCES:
        return jsonify({"ok": False, "error": "Sumber tidak valid."}), 400

    try:
        limit = min(500, max(1, int(request.args.get("limit", "250"))))
    except ValueError:
        limit = 250

    try:
        delete_expired_news()
        rows = query_news(category, source, important, saved, limit)
        return jsonify(
            {
                "ok": True,
                "news": [serialize_row(row) for row in rows],
                "stats": news_stats(),
                "refresh": refresh_state(),
            }
        )
    except Exception:
        return jsonify({"ok": False, "error": "Database berita sedang tidak tersedia."}), 503


@news_bp.post("/refresh")
def manual_refresh():
    try:
        from services.feeds import refresh_news
        result = refresh_news()
        status = 200 if result.get("ok") else 503
        return jsonify({"ok": result.get("ok", False), "refresh": result}), status
    except Exception as exc:
        return jsonify({"ok": False, "error": "Refresh berita gagal.", "detail": str(exc)[:200]}), 503


@news_bp.patch("/news/<int:news_id>/saved")
def update_saved(news_id: int):
    payload = request.get_json(silent=True) or {}
    if "saved" not in payload or not isinstance(payload["saved"], bool):
        return jsonify({"ok": False, "error": "Field saved harus true atau false."}), 400
    try:
        if not set_saved(news_id, payload["saved"]):
            return jsonify({"ok": False, "error": "Berita tidak ditemukan."}), 404
        return jsonify({"ok": True, "id": news_id, "saved": payload["saved"]})
    except Exception:
        return jsonify({"ok": False, "error": "Gagal menyimpan perubahan."}), 503

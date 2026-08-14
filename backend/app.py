import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS

from database import init_db
from routes.news import news_bp
from services.scheduler_service import start_scheduler

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def cors_origins():
    raw = os.getenv("CORS_ORIGINS", "*").strip()
    if raw == "*":
        return "*"
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or "*"


def create_app():
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    CORS(
        app,
        resources={r"/api/*": {"origins": cors_origins()}},
        supports_credentials=False,
    )

    init_db()
    app.register_blueprint(news_bp, url_prefix="/api")

    @app.get("/")
    def root():
        return jsonify(
            {
                "ok": True,
                "service": "MabaCrypto News API",
                "health": "/api/health",
            }
        )

    @app.get("/api/health")
    def health():
        # Deliberately independent from RSS, scheduler, translation and external sources.
        return jsonify({"ok": True, "service": "MabaCrypto News API"})

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"ok": False, "error": "Endpoint tidak ditemukan."}), 404

    @app.errorhandler(500)
    def server_error(_):
        return jsonify({"ok": False, "error": "Internal server error."}), 500

    return app


app = create_app()

# Scheduler failure must never prevent the API from starting.
try:
    if os.getenv("DISABLE_SCHEDULER", "0").lower() not in {"1", "true", "yes"}:
        start_scheduler()
except Exception:
    logger.exception("Scheduler failed to start; API remains available.")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)

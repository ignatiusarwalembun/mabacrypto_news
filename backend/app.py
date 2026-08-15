import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS

from routes.news import news_bp
from services.database import init_db
from services.scheduler import start_scheduler_safely

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)

    origins_raw = os.getenv("CORS_ORIGINS", "*").strip()
    origins = "*" if origins_raw == "*" else [x.strip() for x in origins_raw.split(",") if x.strip()]
    CORS(app, resources={r"/api/*": {"origins": origins}})

    @app.get("/")
    def root():
        return jsonify({"ok": True, "service": "MabaCrypto News API", "health": "/api/health"})

    @app.get("/api/health")
    def health():
        # Intentionally independent from DB, RSS, scheduler and translation.
        return jsonify({"ok": True, "service": "MabaCrypto News API"})

    app.register_blueprint(news_bp, url_prefix="/api")

    # DB/news features can fail without making the health endpoint disappear.
    try:
        init_db()
    except Exception:
        logger.exception("Database initialization failed; health endpoint remains available")

    try:
        start_scheduler_safely()
    except Exception:
        logger.exception("Scheduler startup failed; API remains available")

    return app


app = create_app()
application = app  # Lets the requested `gunicorn app` command work.


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")

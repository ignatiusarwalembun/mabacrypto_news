import os

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

load_dotenv()

from routes.news import news_bp
from services.database import init_db
from services.refresher import refresh_news


def _cors_origins():
    raw = os.getenv("CORS_ORIGINS", "*").strip()
    if not raw or raw == "*":
        return "*"
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app():
    app = Flask(__name__)

    CORS(
        app,
        resources={r"/api/*": {"origins": _cors_origins()}},
        methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    init_db()
    app.register_blueprint(news_bp)

    @app.get("/")
    def root_health():
        return jsonify({
            "ok": True,
            "service": "MabaCrypto News API",
            "health": "/api/health",
            "news": "/api/news",
        })

    return app


app = create_app()


def start_scheduler():
    try:
        minutes = max(5, int(os.getenv("NEWS_REFRESH_MINUTES", "20")))
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(
            refresh_news,
            "interval",
            minutes=minutes,
            id="refresh-news",
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        return scheduler
    except Exception as exc:
        # Scheduler failure must never prevent the web API from starting.
        print(f"[scheduler] disabled because startup failed: {exc}", flush=True)
        return None


scheduler = start_scheduler()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

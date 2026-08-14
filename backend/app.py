import os

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

load_dotenv()

from routes.news import news_bp
from services.database import init_db
from services.refresher import refresh_news, refresh_news_async


def create_app():
    app = Flask(__name__)
    origins = os.getenv("CORS_ORIGINS", "*")
    CORS(app, resources={r"/api/*": {"origins": origins}})
    init_db()
    app.register_blueprint(news_bp)
    return app


app = create_app()


def start_scheduler():
    minutes = max(5, int(os.getenv("NEWS_REFRESH_MINUTES", "20")))
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(refresh_news, "interval", minutes=minutes, id="refresh-news", max_instances=1, coalesce=True)
    scheduler.start()
    return scheduler


scheduler = start_scheduler()

# Warm the news cache without delaying Gunicorn/Railway readiness.
# The HTTP server can become healthy immediately while feeds load behind it.
refresh_news_async()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

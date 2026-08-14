import logging
import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from services.news_service import refresh_news

logger = logging.getLogger(__name__)
_scheduler = None


def start_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    minutes = max(5, int(os.getenv("NEWS_REFRESH_MINUTES", "20")))
    scheduler = BackgroundScheduler(timezone="UTC", daemon=True)
    scheduler.add_job(
        refresh_news,
        "interval",
        minutes=minutes,
        id="news-refresh",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=4),
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("News scheduler started with interval %s minutes", minutes)
    return scheduler

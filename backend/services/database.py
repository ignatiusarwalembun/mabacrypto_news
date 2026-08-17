import os
import sqlite3
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

_DB_LOCK = Lock()


def database_path() -> str:
    configured = os.getenv("DATABASE_PATH", "").strip()
    if configured:
        return configured
    return str(Path(__file__).resolve().parents[1] / "data" / "news.db")


def ensure_database_directory() -> None:
    path = Path(database_path())
    path.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def connection():
    ensure_database_directory()
    conn = sqlite3.connect(database_path(), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _DB_LOCK, connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint TEXT NOT NULL UNIQUE,
                title_original TEXT NOT NULL,
                summary_original TEXT NOT NULL,
                title_id TEXT,
                summary_id TEXT,
                language TEXT NOT NULL DEFAULT 'unknown',
                publisher TEXT NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                published_at TEXT NOT NULL,
                original_url TEXT NOT NULL,
                importance_score INTEGER NOT NULL DEFAULT 0,
                importance_level TEXT NOT NULL DEFAULT 'NORMAL',
                saved INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_news_published_at ON news(published_at DESC);
            CREATE INDEX IF NOT EXISTS idx_news_category ON news(category);
            CREATE INDEX IF NOT EXISTS idx_news_source ON news(source);
            CREATE INDEX IF NOT EXISTS idx_news_saved ON news(saved);
            CREATE INDEX IF NOT EXISTS idx_news_importance ON news(importance_score DESC);

            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        # Kontan is no longer an active source; remove any records left from older versions.
        conn.execute("DELETE FROM news WHERE source = 'KONTAN'")


def upsert_news(article: dict) -> bool:
    with _DB_LOCK, connection() as conn:
        existing = conn.execute(
            "SELECT id FROM news WHERE fingerprint = ?", (article["fingerprint"],)
        ).fetchone()
        conn.execute(
            """
            INSERT INTO news (
                fingerprint, title_original, summary_original, title_id, summary_id,
                language, publisher, source, category, published_at, original_url,
                importance_score, importance_level, saved, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            ON CONFLICT(fingerprint) DO UPDATE SET
                title_original = CASE
                    WHEN news.source = 'BLOOMBERG' AND excluded.source = 'GOOGLE NEWS' THEN news.title_original
                    ELSE excluded.title_original
                END,
                summary_original = CASE
                    WHEN news.source = 'BLOOMBERG' AND excluded.source = 'GOOGLE NEWS' THEN news.summary_original
                    ELSE excluded.summary_original
                END,
                title_id = COALESCE(excluded.title_id, news.title_id),
                summary_id = COALESCE(excluded.summary_id, news.summary_id),
                language = CASE
                    WHEN news.source = 'BLOOMBERG' AND excluded.source = 'GOOGLE NEWS' THEN news.language
                    ELSE excluded.language
                END,
                publisher = CASE
                    WHEN news.source = 'BLOOMBERG' AND excluded.source = 'GOOGLE NEWS' THEN news.publisher
                    ELSE excluded.publisher
                END,
                source = CASE
                    WHEN news.source = 'BLOOMBERG' AND excluded.source = 'GOOGLE NEWS' THEN news.source
                    ELSE excluded.source
                END,
                category = CASE
                    WHEN news.source = 'BLOOMBERG' AND excluded.source = 'GOOGLE NEWS' THEN news.category
                    ELSE excluded.category
                END,
                published_at = CASE
                    WHEN news.source = 'BLOOMBERG' AND excluded.source = 'GOOGLE NEWS' THEN news.published_at
                    ELSE excluded.published_at
                END,
                original_url = CASE
                    WHEN news.source = 'BLOOMBERG' AND excluded.source = 'GOOGLE NEWS' THEN news.original_url
                    ELSE excluded.original_url
                END,
                importance_score = CASE
                    WHEN news.source = 'BLOOMBERG' AND excluded.source = 'GOOGLE NEWS' THEN news.importance_score
                    ELSE excluded.importance_score
                END,
                importance_level = CASE
                    WHEN news.source = 'BLOOMBERG' AND excluded.source = 'GOOGLE NEWS' THEN news.importance_level
                    ELSE excluded.importance_level
                END,
                updated_at = excluded.updated_at
            """,
            (
                article["fingerprint"],
                article["title_original"],
                article["summary_original"],
                article.get("title_id"),
                article.get("summary_id"),
                article.get("language", "unknown"),
                article["publisher"],
                article["source"],
                article["category"],
                article["published_at"],
                article["original_url"],
                article["importance_score"],
                article["importance_level"],
                article["created_at"],
                article["updated_at"],
            ),
        )
        return existing is None



def delete_expired_news(retention_days: int | None = None) -> int:
    """Delete articles older than the retention window based on publication time."""
    if retention_days is None:
        try:
            retention_days = max(1, int(os.getenv("NEWS_RETENTION_DAYS", "10")))
        except ValueError:
            retention_days = 10

    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
    with _DB_LOCK, connection() as conn:
        cursor = conn.execute(
            "DELETE FROM news WHERE datetime(published_at) < datetime(?)",
            (cutoff,),
        )
        return cursor.rowcount

def query_news(category=None, source=None, important=False, saved=False, limit=250):
    clauses = []
    params = []
    if category:
        clauses.append("category = ?")
        params.append(category)
    if source:
        clauses.append("source = ?")
        params.append(source)
    if important:
        clauses.append("importance_score >= 70")
    if saved:
        clauses.append("saved = 1")

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    with connection() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM news
            {where}
            ORDER BY datetime(published_at) DESC, id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def news_stats() -> dict:
    with connection() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN importance_score >= 70 THEN 1 ELSE 0 END) AS important,
                SUM(CASE WHEN category = 'Technology' THEN 1 ELSE 0 END) AS technology,
                SUM(CASE WHEN category = 'Investment' THEN 1 ELSE 0 END) AS investment,
                SUM(CASE WHEN category = 'Blockchain & Crypto' THEN 1 ELSE 0 END) AS crypto
            FROM news
            """
        ).fetchone()
    return {k: int(row[k] or 0) for k in row.keys()}


def set_saved(news_id: int, saved: bool) -> bool:
    with _DB_LOCK, connection() as conn:
        cursor = conn.execute(
            "UPDATE news SET saved = ?, updated_at = datetime('now') WHERE id = ?",
            (1 if saved else 0, news_id),
        )
        return cursor.rowcount > 0


def update_translation(fingerprint: str, title_id: str | None, summary_id: str | None) -> None:
    with _DB_LOCK, connection() as conn:
        conn.execute(
            """
            UPDATE news
            SET title_id = COALESCE(?, title_id),
                summary_id = COALESCE(?, summary_id),
                updated_at = datetime('now')
            WHERE fingerprint = ?
            """,
            (title_id, summary_id, fingerprint),
        )


def set_state(key: str, value: str, updated_at: str) -> None:
    with _DB_LOCK, connection() as conn:
        conn.execute(
            """
            INSERT INTO app_state(key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, value, updated_at),
        )


def get_state(key: str):
    with connection() as conn:
        row = conn.execute("SELECT value, updated_at FROM app_state WHERE key = ?", (key,)).fetchone()
    return dict(row) if row else None

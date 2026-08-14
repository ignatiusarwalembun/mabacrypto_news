import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "news.db"


def get_db_path() -> Path:
    raw = os.getenv("DATABASE_PATH", str(DEFAULT_DB_PATH))
    path = Path(raw).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_connection():
    conn = sqlite3.connect(get_db_path(), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                original_title TEXT NOT NULL,
                original_summary TEXT NOT NULL,
                publisher TEXT NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                published_at TEXT NOT NULL,
                original_url TEXT NOT NULL,
                discovery_url TEXT,
                importance_score INTEGER NOT NULL DEFAULT 0,
                importance_level TEXT NOT NULL DEFAULT 'NORMAL',
                saved INTEGER NOT NULL DEFAULT 0 CHECK(saved IN (0,1)),
                translated INTEGER NOT NULL DEFAULT 0 CHECK(translated IN (0,1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_news_published_at ON news(published_at DESC);
            CREATE INDEX IF NOT EXISTS idx_news_category ON news(category);
            CREATE INDEX IF NOT EXISTS idx_news_source ON news(source);
            CREATE INDEX IF NOT EXISTS idx_news_saved ON news(saved);
            CREATE INDEX IF NOT EXISTS idx_news_importance ON news(importance_score DESC);
            """
        )


def find_by_fingerprint(fingerprint: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM news WHERE fingerprint = ? LIMIT 1", (fingerprint,)
        ).fetchone()
        return dict(row) if row else None


def upsert_news(article: dict) -> int:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO news (
                fingerprint, title, summary, original_title, original_summary,
                publisher, source, category, published_at, original_url,
                discovery_url, importance_score, importance_level, translated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(fingerprint) DO UPDATE SET
                title = excluded.title,
                summary = excluded.summary,
                original_title = excluded.original_title,
                original_summary = excluded.original_summary,
                publisher = excluded.publisher,
                source = excluded.source,
                category = excluded.category,
                published_at = excluded.published_at,
                original_url = excluded.original_url,
                discovery_url = excluded.discovery_url,
                importance_score = excluded.importance_score,
                importance_level = excluded.importance_level,
                translated = excluded.translated,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                article["fingerprint"],
                article["title"],
                article["summary"],
                article["original_title"],
                article["original_summary"],
                article["publisher"],
                article["source"],
                article["category"],
                article["published_at"],
                article["original_url"],
                article.get("discovery_url"),
                article["importance_score"],
                article["importance_level"],
                1 if article.get("translated") else 0,
            ),
        )
        row = conn.execute(
            "SELECT id FROM news WHERE fingerprint = ?", (article["fingerprint"],)
        ).fetchone()
        return int(row["id"])


def list_news(
    category: str | None = None,
    source: str | None = None,
    saved: bool | None = None,
    important: bool | None = None,
    search: str | None = None,
    limit: int = 250,
):
    where = []
    params = []

    if category:
        where.append("category = ?")
        params.append(category)
    if source:
        where.append("source = ?")
        params.append(source)
    if saved is not None:
        where.append("saved = ?")
        params.append(1 if saved else 0)
    if important:
        where.append("importance_score >= 70")
    if search:
        where.append("(title LIKE ? OR summary LIKE ? OR publisher LIKE ?)")
        q = f"%{search}%"
        params.extend([q, q, q])

    sql = "SELECT * FROM news"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY datetime(published_at) DESC, id DESC LIMIT ?"
    params.append(max(1, min(limit, 500)))

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]


def update_saved(news_id: int, saved: bool):
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE news SET saved = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (1 if saved else 0, news_id),
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute("SELECT * FROM news WHERE id = ?", (news_id,)).fetchone()
        return dict(row)


def get_stats():
    with get_connection() as conn:
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
        data = dict(row)
        return {key: int(value or 0) for key, value in data.items()}

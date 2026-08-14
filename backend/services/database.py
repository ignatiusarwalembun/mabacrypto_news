import os
import sqlite3
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "data", "news.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS news (
    id TEXT PRIMARY KEY,
    title_original TEXT NOT NULL,
    title_id TEXT NOT NULL,
    summary_original TEXT DEFAULT '',
    summary_id TEXT DEFAULT '',
    url TEXT NOT NULL,
    source TEXT NOT NULL,
    publisher TEXT DEFAULT '',
    category TEXT NOT NULL,
    published_at TEXT DEFAULT '',
    importance_score INTEGER DEFAULT 0,
    importance_level TEXT DEFAULT 'normal',
    importance_reason TEXT DEFAULT '',
    is_saved INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_news_published_at ON news(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_source ON news(source);
CREATE INDEX IF NOT EXISTS idx_news_category ON news(category);
CREATE INDEX IF NOT EXISTS idx_news_importance ON news(importance_score DESC);
"""

@contextmanager
def connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with connection() as conn:
        conn.executescript(SCHEMA)


def upsert_news(item):
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO news (
                id, title_original, title_id, summary_original, summary_id,
                url, source, publisher, category, published_at,
                importance_score, importance_level, importance_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title_id=excluded.title_id,
                summary_id=excluded.summary_id,
                publisher=excluded.publisher,
                category=excluded.category,
                importance_score=excluded.importance_score,
                importance_level=excluded.importance_level,
                importance_reason=excluded.importance_reason
            """,
            (
                item["id"], item["title_original"], item["title_id"],
                item.get("summary_original", ""), item.get("summary_id", ""),
                item["url"], item["source"], item.get("publisher", ""),
                item["category"], item.get("published_at", ""),
                item.get("importance_score", 0), item.get("importance_level", "normal"),
                item.get("importance_reason", "")
            ),
        )


def query_news(category=None, source=None, important=False, saved=False, search=None, limit=80):
    clauses = []
    params = []
    if category and category != "all":
        clauses.append("category = ?")
        params.append(category)
    if source and source != "all":
        clauses.append("source = ?")
        params.append(source)
    if important:
        clauses.append("importance_score >= 70")
    if saved:
        clauses.append("is_saved = 1")
    if search:
        clauses.append("(title_id LIKE ? OR summary_id LIKE ? OR title_original LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])

    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    sql = f"""
        SELECT * FROM news
        {where}
        ORDER BY
            CASE WHEN published_at = '' THEN 1 ELSE 0 END,
            published_at DESC,
            importance_score DESC
        LIMIT ?
    """
    params.append(max(1, min(int(limit), 200)))
    with connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def count_news():
    with connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]


def set_saved(news_id, is_saved):
    with connection() as conn:
        cur = conn.execute("UPDATE news SET is_saved = ? WHERE id = ?", (1 if is_saved else 0, news_id))
        return cur.rowcount > 0


def stats():
    with connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]
        important = conn.execute("SELECT COUNT(*) FROM news WHERE importance_score >= 70").fetchone()[0]
        technology = conn.execute("SELECT COUNT(*) FROM news WHERE category = 'technology'").fetchone()[0]
        investment = conn.execute("SELECT COUNT(*) FROM news WHERE category = 'investment'").fetchone()[0]
        crypto = conn.execute("SELECT COUNT(*) FROM news WHERE category = 'crypto'").fetchone()[0]
    return {"total": total, "important": important, "technology": technology, "investment": investment, "crypto": crypto}


def existing_ids(ids):
    if not ids:
        return set()
    placeholders = ",".join("?" for _ in ids)
    with connection() as conn:
        rows = conn.execute(f"SELECT id FROM news WHERE id IN ({placeholders})", ids).fetchall()
    return {row[0] for row in rows}

import hashlib
import html
import logging
import re
import threading
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse

import feedparser
import requests
from googlenewsdecoder import gnewsdecoder

from database import find_by_fingerprint, upsert_news
from services.importance_service import score_importance
from services.translation_service import translate_to_indonesian

logger = logging.getLogger(__name__)

REQUEST_HEADERS = {
    "User-Agent": "MabaCryptoNews/1.0 (+news aggregator; public RSS discovery)"
}
REQUEST_TIMEOUT = 18

# Google News RSS is used as a public discovery surface. Bloomberg/Kontan queries
# intentionally use site: filters instead of scraping publisher pages.
FEEDS = [
    {
        "name": "Google News Indonesia",
        "source": "GOOGLE NEWS",
        "lang": "id",
        "country": "ID",
        "query": "(investasi OR saham OR teknologi OR AI OR bitcoin OR ethereum OR kripto OR blockchain OR inflasi OR suku bunga OR IPO) when:2d",
    },
    {
        "name": "Google News Global",
        "source": "GOOGLE NEWS",
        "lang": "en",
        "country": "US",
        "query": "(investment OR stocks OR technology OR AI OR bitcoin OR ethereum OR cryptocurrency OR blockchain OR inflation OR interest rate OR IPO) when:2d",
    },
    {
        "name": "Bloomberg via Google News",
        "source": "BLOOMBERG",
        "lang": "en",
        "country": "US",
        "query": "site:bloomberg.com (markets OR investment OR technology OR AI OR bitcoin OR ethereum OR crypto OR Federal Reserve) when:3d",
    },
    {
        "name": "Kontan via Google News",
        "source": "KONTAN",
        "lang": "id",
        "country": "ID",
        "query": "site:kontan.co.id (investasi OR saham OR teknologi OR AI OR bitcoin OR ethereum OR kripto OR blockchain OR ekonomi) when:3d",
    },
]

STATE_LOCK = threading.Lock()
REFRESH_LOCK = threading.Lock()
REFRESH_STATE = {
    "running": False,
    "last_attempt": None,
    "last_success": None,
    "source_errors": {},
    "last_inserted_or_updated": 0,
}

CATEGORY_KEYWORDS = {
    "Blockchain & Crypto": (
        "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency",
        "kripto", "blockchain", "web3", "token", "stablecoin", "defi", "etf bitcoin",
    ),
    "Technology": (
        "technology", "teknologi", "artificial intelligence", " ai ", "openai",
        "nvidia", "microsoft", "google", "apple", "meta", "semiconductor",
        "semikonduktor", "chip", "software", "cloud", "robot",
    ),
    "Investment": (
        "investment", "investasi", "stock", "stocks", "saham", "market", "pasar",
        "ihsg", "inflation", "inflasi", "interest rate", "suku bunga", "federal reserve",
        "fed", "ipo", "funding", "pendanaan", "merger", "acquisition", "akuisisi",
        "bankruptcy", "obligasi", "bond", "recession", "resesi",
    ),
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_refresh_state() -> dict:
    with STATE_LOCK:
        return {
            "running": REFRESH_STATE["running"],
            "last_attempt": REFRESH_STATE["last_attempt"],
            "last_success": REFRESH_STATE["last_success"],
            "source_errors": dict(REFRESH_STATE["source_errors"]),
            "last_inserted_or_updated": REFRESH_STATE["last_inserted_or_updated"],
        }


def build_feed_url(feed: dict) -> str:
    lang = feed["lang"]
    country = feed["country"]
    ceid = f"{country}:{lang}"
    return (
        "https://news.google.com/rss/search?q="
        f"{quote_plus(feed['query'])}&hl={lang}-{country}&gl={country}&ceid={ceid}"
    )


def strip_html(value: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", value or "", flags=re.I | re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def clean_title(raw_title: str, publisher: str) -> str:
    title = strip_html(raw_title)
    if publisher:
        suffix = f" - {publisher}".lower()
        if title.lower().endswith(suffix):
            title = title[: -len(suffix)].strip()
    return title


def build_summary(entry, title: str, publisher: str) -> str:
    raw = entry.get("summary") or entry.get("description") or ""
    summary = strip_html(raw)

    # Google News descriptions sometimes repeat the title and publisher.
    for fragment in (title, publisher):
        if fragment and summary.lower().startswith(fragment.lower()):
            summary = summary[len(fragment):].lstrip(" -:—")

    if not summary or len(summary) < 24:
        summary = f"{publisher} melaporkan perkembangan terbaru terkait: {title}."

    if len(summary) > 430:
        summary = summary[:427].rstrip() + "..."
    return summary


def parse_published(entry) -> str:
    raw = entry.get("published") or entry.get("updated")
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass
    return utc_now_iso()


def extract_publisher(entry, fallback_source: str) -> str:
    source = entry.get("source")
    if isinstance(source, dict):
        name = source.get("title")
        if name:
            return strip_html(name)
    if hasattr(source, "title") and source.title:
        return strip_html(source.title)
    if fallback_source == "BLOOMBERG":
        return "Bloomberg"
    if fallback_source == "KONTAN":
        return "Kontan"
    return "Google News"


def categorize(title: str, summary: str) -> str:
    text = f" {title} {summary} ".lower()
    scores = {}
    for category, words in CATEGORY_KEYWORDS.items():
        scores[category] = sum(1 for word in words if word in text)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Investment"


def fingerprint_for(title: str, publisher: str) -> str:
    normalized = re.sub(r"\W+", " ", f"{title} {publisher}".lower()).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def decode_original_url(discovery_url: str) -> str:
    if not discovery_url:
        return ""
    try:
        parsed = urlparse(discovery_url)
        if "news.google.com" not in parsed.netloc:
            return discovery_url
        result = gnewsdecoder(discovery_url, interval=0.05)
        if isinstance(result, dict) and result.get("status") and result.get("decoded_url"):
            return result["decoded_url"]
    except Exception:
        logger.debug("Could not decode Google News URL", exc_info=True)
    return discovery_url


def process_entry(entry, feed: dict) -> bool:
    publisher = extract_publisher(entry, feed["source"])
    original_title = clean_title(entry.get("title", ""), publisher)
    if not original_title:
        return False

    original_summary = build_summary(entry, original_title, publisher)
    fingerprint = fingerprint_for(original_title, publisher)
    existing = find_by_fingerprint(fingerprint)

    if existing:
        title = existing["title"]
        summary = existing["summary"]
        translated = bool(existing["translated"])
    else:
        title, summary, translated = translate_to_indonesian(
            original_title, original_summary
        )

    category = categorize(original_title, original_summary)
    importance_score, importance_level = score_importance(
        original_title, original_summary
    )
    discovery_url = entry.get("link", "")
    original_url = decode_original_url(discovery_url)

    article = {
        "fingerprint": fingerprint,
        "title": title,
        "summary": summary,
        "original_title": original_title,
        "original_summary": original_summary,
        "publisher": publisher,
        "source": feed["source"],
        "category": category,
        "published_at": parse_published(entry),
        "original_url": original_url or discovery_url,
        "discovery_url": discovery_url,
        "importance_score": importance_score,
        "importance_level": importance_level,
        "translated": translated,
    }
    upsert_news(article)
    return True


def fetch_feed(feed: dict) -> int:
    url = build_feed_url(feed)
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    if getattr(parsed, "bozo", False) and not parsed.entries:
        raise RuntimeError(f"RSS parse error: {getattr(parsed, 'bozo_exception', 'unknown')}")

    processed = 0
    for entry in parsed.entries[:45]:
        try:
            if process_entry(entry, feed):
                processed += 1
        except Exception:
            logger.exception("Failed to process one article from %s", feed["name"])
    return processed


def refresh_news() -> dict:
    if not REFRESH_LOCK.acquire(blocking=False):
        return {"ok": True, "already_running": True, **get_refresh_state()}

    errors = {}
    processed_total = 0
    attempt = utc_now_iso()
    with STATE_LOCK:
        REFRESH_STATE["running"] = True
        REFRESH_STATE["last_attempt"] = attempt
        REFRESH_STATE["source_errors"] = {}

    try:
        for feed in FEEDS:
            try:
                processed_total += fetch_feed(feed)
            except Exception as exc:
                errors[feed["name"]] = str(exc)[:300]
                logger.exception("Feed failed: %s", feed["name"])

        with STATE_LOCK:
            REFRESH_STATE["running"] = False
            REFRESH_STATE["source_errors"] = errors
            REFRESH_STATE["last_inserted_or_updated"] = processed_total
            if processed_total > 0:
                REFRESH_STATE["last_success"] = utc_now_iso()

        return {
            "ok": processed_total > 0 or not errors,
            "processed": processed_total,
            "errors": errors,
            "partial_failure": bool(errors) and processed_total > 0,
        }
    finally:
        with STATE_LOCK:
            REFRESH_STATE["running"] = False
        REFRESH_LOCK.release()

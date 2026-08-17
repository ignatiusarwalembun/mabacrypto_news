import hashlib
import html
import logging
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse

import feedparser
import requests

from services.database import delete_expired_news, set_state, upsert_news
from services.scoring import score_importance
from services.translator import detect_language, queue_translation

logger = logging.getLogger(__name__)

USER_AGENT = "MabaCryptoNews/1.0 (+news aggregator; RSS metadata only)"
REQUEST_TIMEOUT = int(os.getenv("NEWS_REQUEST_TIMEOUT_SECONDS", "15"))
MAX_ITEMS_PER_FEED = int(os.getenv("MAX_ITEMS_PER_FEED", "35"))

# Public RSS feeds. No article-body scraping and no paywall bypass.
BLOOMBERG_FEEDS = [
    ("https://feeds.bloomberg.com/markets/news.rss", "Investment"),
    ("https://feeds.bloomberg.com/technology/news.rss", "Technology"),
    ("https://feeds.bloomberg.com/crypto/news.rss", "Blockchain & Crypto"),
]


GOOGLE_NEWS_QUERIES = [
    ("investment OR stocks OR market OR IPO OR inflation OR interest rate when:2d", "Investment"),
    ("technology OR semiconductor OR NVIDIA OR Microsoft OR Google OR Apple OR Meta when:2d", "Technology"),
    ("bitcoin OR ethereum OR cryptocurrency OR blockchain OR crypto ETF when:2d", "Blockchain & Crypto"),
]


def google_news_url(query: str, language="en-US", country="US", edition="US:en") -> str:
    return f"https://news.google.com/rss/search?q={quote_plus(query)}&hl={language}&gl={country}&ceid={edition}"


def clean_text(value: str) -> str:
    if not value:
        return ""
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_title(title: str) -> str:
    normalized = title.lower()
    normalized = re.sub(r"\s+-\s+(bloomberg|google news)\s*$", "", normalized)
    normalized = re.sub(r"[^a-z0-9\u00c0-\u024f\u1e00-\u1eff]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def fingerprint_for(title: str) -> str:
    return hashlib.sha256(normalize_title(title).encode("utf-8")).hexdigest()


def parse_date(entry) -> str:
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                pass
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()


def publisher_from_entry(entry, fallback: str) -> str:
    source = getattr(entry, "source", None)
    if isinstance(source, dict):
        title = clean_text(source.get("title", ""))
        if title:
            return title
    author = clean_text(getattr(entry, "author", ""))
    return author or fallback


def resolve_public_redirect(url: str) -> str:
    """Follow ordinary HTTP redirects only; never scrape publisher content.

    Google News RSS may keep a Google redirect page instead of returning a normal
    HTTP redirect. In that case we keep the public Google News URL, which still
    leads the user to the publisher when opened in a browser.
    """
    if not url or "news.google.com" not in urlparse(url).netloc:
        return url
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=min(REQUEST_TIMEOUT, 8),
            allow_redirects=True,
            stream=True,
        )
        final = response.url
        response.close()
        if final and "news.google.com" not in urlparse(final).netloc:
            return final
    except Exception:
        pass
    return url


def infer_category(title: str, summary: str, hint: str) -> str:
    text = f"{title} {summary}".lower()
    crypto = ["bitcoin", "btc", "ethereum", "ether", "crypto", "cryptocurrency", "blockchain", "web3", "stablecoin"]
    tech = ["technology", "teknologi", "ai ", "artificial intelligence", "semiconductor", "chip", "nvidia", "microsoft", "apple", "meta", "software"]
    investment = ["investment", "investasi", "stock", "saham", "market", "pasar", "ipo", "fund", "funding", "bank", "inflation", "inflasi", "interest rate", "suku bunga"]
    if any(k in text for k in crypto):
        return "Blockchain & Crypto"
    if any(k in text for k in tech):
        return "Technology"
    if any(k in text for k in investment):
        return "Investment"
    return hint


def fetch_feed(url: str):
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    if getattr(parsed, "bozo", False) and not parsed.entries:
        raise RuntimeError(f"Invalid RSS response: {getattr(parsed, 'bozo_exception', 'unknown error')}")
    return parsed.entries[:MAX_ITEMS_PER_FEED]


def article_from_entry(entry, source: str, category_hint: str, publisher_fallback: str) -> dict | None:
    title = clean_text(getattr(entry, "title", ""))
    link = (getattr(entry, "link", "") or "").strip()
    if not title or not link:
        return None

    summary = clean_text(getattr(entry, "summary", "") or getattr(entry, "description", ""))
    if not summary:
        summary = "Ringkasan tidak tersedia di feed publik. Buka sumber asli untuk membaca artikel."
    summary = summary[:1000]

    publisher = publisher_from_entry(entry, publisher_fallback)
    category = infer_category(title, summary, category_hint)
    language = detect_language(f"{title}. {summary[:300]}")

    # Store the article immediately. English translation is queued separately so
    # feed refresh and the API are never blocked by a translation service.
    title_id = None
    summary_id = None
    score, level = score_importance(title, summary)
    now = datetime.now(timezone.utc).isoformat()

    fingerprint = fingerprint_for(title)

    return {
        "fingerprint": fingerprint,
        "title_original": title,
        "summary_original": summary,
        "title_id": title_id,
        "summary_id": summary_id,
        "language": language,
        "publisher": publisher,
        "source": source,
        "category": category,
        "published_at": parse_date(entry),
        "original_url": resolve_public_redirect(link),
        "importance_score": score,
        "importance_level": level,
        "created_at": now,
        "updated_at": now,
    }


def _refresh_feed(url: str, source: str, hint: str, publisher: str) -> tuple[int, int]:
    fetched = 0
    inserted = 0
    for entry in fetch_feed(url):
        fetched += 1
        try:
            article = article_from_entry(entry, source, hint, publisher)
            if article:
                if upsert_news(article):
                    inserted += 1
                if article.get("language") == "en":
                    queue_translation(
                        article["fingerprint"],
                        article["title_original"],
                        article["summary_original"],
                    )
        except Exception as exc:
            logger.warning("Skipping one %s article: %s", source, exc)
    return fetched, inserted


def refresh_news() -> dict:
    started = datetime.now(timezone.utc).isoformat()
    results = {
        "started_at": started,
        "finished_at": None,
        "sources": {},
        "total_fetched": 0,
        "total_inserted": 0,
    }

    source_groups = {
        "BLOOMBERG": [(url, hint, "Bloomberg") for url, hint in BLOOMBERG_FEEDS],
        "GOOGLE NEWS": [(google_news_url(query), hint, "Google News") for query, hint in GOOGLE_NEWS_QUERIES],
    }

    for source_name, feeds in source_groups.items():
        status = {"ok": False, "fetched": 0, "inserted": 0, "errors": []}
        for url, hint, publisher in feeds:
            try:
                fetched, inserted = _refresh_feed(url, source_name, hint, publisher)
                status["ok"] = True
                status["fetched"] += fetched
                status["inserted"] += inserted
            except Exception as exc:
                logger.warning("Feed failed (%s): %s", url, exc)
                status["errors"].append(str(exc)[:240])

        # Public Google News discovery fallback for Bloomberg if direct RSS is unavailable.
        if not status["ok"] and source_name == "BLOOMBERG":
            domain = "bloomberg.com"
            fallback_queries = [
                (f"site:{domain} investment OR market OR economy when:2d", "Investment"),
                (f"site:{domain} technology OR AI OR semiconductor when:2d", "Technology"),
                (f"site:{domain} bitcoin OR crypto OR blockchain when:2d", "Blockchain & Crypto"),
            ]
            for query, hint in fallback_queries:
                try:
                    fetched, inserted = _refresh_feed(
                        google_news_url(query), source_name, hint,
                        "Bloomberg",
                    )
                    status["ok"] = True
                    status["fetched"] += fetched
                    status["inserted"] += inserted
                except Exception as exc:
                    status["errors"].append(f"fallback: {str(exc)[:200]}")

        results["sources"][source_name] = status
        results["total_fetched"] += status["fetched"]
        results["total_inserted"] += status["inserted"]

    finished = datetime.now(timezone.utc).isoformat()
    results["finished_at"] = finished
    results["ok"] = any(v["ok"] for v in results["sources"].values())
    results["partial_failure"] = any(not v["ok"] for v in results["sources"].values())
    try:
        results["expired_deleted"] = delete_expired_news()
    except Exception as exc:
        logger.warning("Could not delete expired news: %s", exc)
        results["expired_deleted"] = 0
    try:
        import json

        set_state("last_refresh", json.dumps(results, ensure_ascii=False), finished)
    except Exception as exc:
        logger.warning("Could not persist refresh state: %s", exc)
    return results

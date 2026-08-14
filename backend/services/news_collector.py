import hashlib
import html
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import feedparser
import requests
from bs4 import BeautifulSoup

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=id&gl=ID&ceid=ID:id"
BING_NEWS_RSS = "https://www.bing.com/news/search?q={query}&format=rss&setlang=id-ID&cc=id"

MAX_ITEMS = int(os.getenv("MAX_ITEMS_PER_FEED", "8"))

FEEDS = [
    {
        "source": "Bloomberg",
        "category": "investment",
        "query": 'site:bloomberg.com (markets OR stocks OR investment OR economy OR inflation OR fed OR bonds OR oil OR gold) when:2d',
        "fallback": True,
    },
    {
        "source": "Bloomberg",
        "category": "technology",
        "query": 'site:bloomberg.com (AI OR artificial intelligence OR technology OR semiconductor OR chip OR robotics OR startup OR cloud OR data center) when:2d',
        "fallback": True,
    },
    {
        "source": "Bloomberg",
        "category": "crypto",
        "query": 'site:bloomberg.com (blockchain OR crypto OR cryptocurrency OR bitcoin OR ethereum OR stablecoin OR tokenization OR web3) when:2d',
        "fallback": True,
    },
    {
        "source": "Kontan",
        "category": "investment",
        "query": 'site:kontan.co.id (investasi OR saham OR IHSG OR rupiah OR emas OR obligasi OR ekonomi OR pasar) when:2d',
        "fallback": True,
    },
    {
        "source": "Kontan",
        "category": "technology",
        "query": 'site:kontan.co.id (teknologi OR AI OR kecerdasan buatan OR chip OR startup OR digital OR data center) when:3d',
        "fallback": True,
    },
    {
        "source": "Kontan",
        "category": "crypto",
        "query": 'site:kontan.co.id (blockchain OR kripto OR cryptocurrency OR bitcoin OR ethereum OR stablecoin OR tokenisasi OR web3) when:3d',
        "fallback": True,
    },
    {
        "source": "Google News",
        "category": "investment",
        "query": '(investasi OR saham OR IHSG OR rupiah OR emas OR obligasi OR "bank sentral" OR inflation OR markets) when:1d',
        "fallback": False,
    },
    {
        "source": "Google News",
        "category": "technology",
        "query": '(AI OR "artificial intelligence" OR teknologi OR semiconductor OR chip OR robotics OR startup OR "data center") when:1d',
        "fallback": False,
    },
    {
        "source": "Google News",
        "category": "crypto",
        "query": '(blockchain OR crypto OR cryptocurrency OR kripto OR bitcoin OR ethereum OR stablecoin OR tokenization OR tokenisasi OR web3) when:1d',
        "fallback": False,
    },
]

_state_lock = threading.Lock()
_collector_state = {
    "last_started_at": None,
    "last_finished_at": None,
    "requests_attempted": 0,
    "requests_succeeded": 0,
    "items_collected": 0,
    "errors": [],
}


def get_collector_state():
    with _state_lock:
        return {
            **_collector_state,
            "errors": list(_collector_state.get("errors", [])),
        }


def clean_html(value):
    if not value:
        return ""
    soup = BeautifulSoup(html.unescape(value), "html.parser")
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def parse_date(entry):
    raw = entry.get("published") or entry.get("updated") or ""
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    try:
        return parsedate_to_datetime(raw).astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def publisher_from_entry(entry):
    source = entry.get("source")
    if isinstance(source, dict):
        return source.get("title", "")
    return ""


def normalize_title(title):
    parts = [p.strip() for p in title.rsplit(" - ", 1)]
    return parts[0] if len(parts) == 2 else title.strip()


def make_id(title, url):
    seed = f"{title.lower().strip()}|{url.strip()}".encode("utf-8")
    return hashlib.sha256(seed).hexdigest()[:24]


def _bing_query(query):
    # Bing does not need Google's time operator. Keep the topical/site filter.
    return re.sub(r"\s+when:\d+d\b", "", query).strip()


def _provider_url(provider, query):
    if provider == "google":
        return GOOGLE_NEWS_RSS.format(query=quote_plus(query))
    if provider == "bing":
        return BING_NEWS_RSS.format(query=quote_plus(_bing_query(query)))
    raise ValueError(f"Unknown provider: {provider}")


def _record_request(success, error=None):
    with _state_lock:
        _collector_state["requests_attempted"] += 1
        if success:
            _collector_state["requests_succeeded"] += 1
        elif error:
            errors = _collector_state.setdefault("errors", [])
            errors.append(error)
            del errors[:-12]


def _fetch_from_provider(feed, provider):
    url = _provider_url(provider, feed["query"])
    provider_name = "Google News RSS" if provider == "google" else "Bing News RSS"

    try:
        response = requests.get(
            url,
            timeout=(4, 10),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/151 Safari/537.36"
                )
            },
        )
        response.raise_for_status()
        parsed = feedparser.parse(response.content)

        if getattr(parsed, "bozo", False) and not parsed.entries:
            raise RuntimeError(f"RSS parse failed: {getattr(parsed, 'bozo_exception', 'unknown')}")

        _record_request(True)
    except Exception as exc:
        _record_request(
            False,
            f'{feed["source"]}/{feed["category"]} via {provider_name}: '
            f"{type(exc).__name__}: {exc}",
        )
        return []

    items = []
    for entry in parsed.entries[:MAX_ITEMS]:
        raw_title = clean_html(entry.get("title", ""))
        title = normalize_title(raw_title)
        if not title:
            continue

        link = entry.get("link", "")
        summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
        publisher = publisher_from_entry(entry)

        items.append({
            "id": make_id(title, link),
            "title_original": title,
            "summary_original": summary,
            "url": link,
            "source": feed["source"],
            "publisher": publisher,
            "category": feed["category"],
            "published_at": parse_date(entry),
        })

    return items


def _fetch_feed(feed):
    # Primary path is Google News RSS for all configured feeds.
    items = _fetch_from_provider(feed, "google")
    if items:
        return items

    # Only Bloomberg/Kontan use Bing as fallback so source labels remain truthful.
    if feed.get("fallback"):
        return _fetch_from_provider(feed, "bing")

    return []


def collect_news():
    started = datetime.now(timezone.utc).isoformat()
    with _state_lock:
        _collector_state.update({
            "last_started_at": started,
            "requests_attempted": 0,
            "requests_succeeded": 0,
            "items_collected": 0,
            "errors": [],
        })

    collected = []
    seen_titles = set()

    workers = min(6, len(FEEDS))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="news-feed") as executor:
        futures = [executor.submit(_fetch_feed, feed) for feed in FEEDS]

        for future in as_completed(futures):
            try:
                items = future.result()
            except Exception as exc:
                _record_request(False, f"worker: {type(exc).__name__}: {exc}")
                continue

            for item in items:
                title = item["title_original"]
                dedupe_key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
                if not dedupe_key or dedupe_key in seen_titles:
                    continue
                seen_titles.add(dedupe_key)
                collected.append(item)

    with _state_lock:
        _collector_state.update({
            "last_finished_at": datetime.now(timezone.utc).isoformat(),
            "items_collected": len(collected),
        })

    return collected

import hashlib
import html
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import feedparser
import requests
from bs4 import BeautifulSoup

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=id&gl=ID&ceid=ID:id"
MAX_ITEMS = int(os.getenv("MAX_ITEMS_PER_FEED", "8"))

FEEDS = [
    {
        "source": "Bloomberg",
        "category": "investment",
        "query": 'site:bloomberg.com (markets OR stocks OR investment OR economy OR inflation OR fed OR bonds OR oil OR gold) when:2d',
    },
    {
        "source": "Bloomberg",
        "category": "technology",
        "query": 'site:bloomberg.com (AI OR artificial intelligence OR technology OR semiconductor OR chip OR robotics OR startup OR cloud OR data center) when:2d',
    },
    {
        "source": "Bloomberg",
        "category": "crypto",
        "query": 'site:bloomberg.com (blockchain OR crypto OR cryptocurrency OR bitcoin OR ethereum OR stablecoin OR tokenization OR web3) when:2d',
    },
    {
        "source": "Kontan",
        "category": "investment",
        "query": 'site:kontan.co.id (investasi OR saham OR IHSG OR rupiah OR emas OR obligasi OR ekonomi OR pasar) when:2d',
    },
    {
        "source": "Kontan",
        "category": "technology",
        "query": 'site:kontan.co.id (teknologi OR AI OR kecerdasan buatan OR chip OR startup OR digital OR data center) when:3d',
    },
    {
        "source": "Kontan",
        "category": "crypto",
        "query": 'site:kontan.co.id (blockchain OR kripto OR cryptocurrency OR bitcoin OR ethereum OR stablecoin OR tokenisasi OR web3) when:3d',
    },
    {
        "source": "Google News",
        "category": "investment",
        "query": '(investasi OR saham OR IHSG OR rupiah OR emas OR obligasi OR "bank sentral" OR inflation OR markets) when:1d',
    },
    {
        "source": "Google News",
        "category": "technology",
        "query": '(AI OR "artificial intelligence" OR teknologi OR semiconductor OR chip OR robotics OR startup OR "data center") when:1d',
    },
    {
        "source": "Google News",
        "category": "crypto",
        "query": '(blockchain OR crypto OR cryptocurrency OR kripto OR bitcoin OR ethereum OR stablecoin OR tokenization OR tokenisasi OR web3) when:1d',
    },
]


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
    # Google News often appends " - Publisher". Keep the article title clean where possible.
    parts = [p.strip() for p in title.rsplit(" - ", 1)]
    return parts[0] if len(parts) == 2 else title.strip()


def make_id(title, url):
    seed = f"{title.lower().strip()}|{url.strip()}".encode("utf-8")
    return hashlib.sha256(seed).hexdigest()[:24]


def _fetch_feed(feed):
    """Fetch and parse one feed. Network failures return an empty list."""
    url = GOOGLE_NEWS_RSS.format(query=quote_plus(feed["query"]))
    try:
        response = requests.get(
            url,
            timeout=(3.5, 8),
            headers={"User-Agent": "MabaCryptoNews/1.0 (+news-dashboard)"},
        )
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
    except requests.RequestException:
        return []

    items = []
    for entry in parsed.entries[:MAX_ITEMS]:
        raw_title = clean_html(entry.get("title", "Untitled"))
        title = normalize_title(raw_title)
        if not title:
            continue

        link = entry.get("link", "")
        summary = clean_html(entry.get("summary", ""))
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


def collect_news():
    """Collect feeds concurrently so refresh time is bounded by slow feeds, not their sum."""
    collected = []
    seen_titles = set()

    workers = min(6, len(FEEDS))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="news-feed") as executor:
        futures = [executor.submit(_fetch_feed, feed) for feed in FEEDS]

        for future in as_completed(futures):
            try:
                items = future.result()
            except Exception:
                continue

            for item in items:
                title = item["title_original"]
                dedupe_key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
                if dedupe_key in seen_titles:
                    continue
                seen_titles.add(dedupe_key)
                collected.append(item)

    return collected

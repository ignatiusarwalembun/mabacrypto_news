import json
import os
import re
from functools import lru_cache

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

IMPORTANT_TERMS = {
    "rate cut": 18, "rate hike": 20, "fed": 12, "bank indonesia": 12,
    "crash": 25, "plunge": 20, "record high": 14, "acquisition": 15,
    "merger": 15, "ipo": 12, "billion": 12, "trillion": 16,
    "semiconductor": 12, "chip": 10, "artificial intelligence": 12, "ai": 8,
    "nvidia": 10, "openai": 10, "google": 7, "microsoft": 7, "apple": 7,
    "rupiah": 7, "ihsg": 7, "inflation": 10, "recession": 18,
    "tariff": 12, "sanction": 14, "war": 18, "oil": 7, "gold": 7,
    "data center": 10, "robot": 9, "robotics": 10,
    "blockchain": 10, "crypto": 9, "cryptocurrency": 9, "kripto": 9,
    "bitcoin": 12, "ethereum": 10, "stablecoin": 12, "tokenization": 9,
    "tokenisasi": 9, "web3": 7, "exchange": 7, "etf": 10,
}


def level_from_score(score):
    if score >= 85:
        return "very-important"
    if score >= 70:
        return "important"
    if score >= 40:
        return "attention"
    return "normal"


def heuristic_analysis(item):
    text = f"{item.get('title_original','')} {item.get('summary_original','')}".lower()
    score = 25
    hits = []
    for term, value in IMPORTANT_TERMS.items():
        if term in text:
            score += value
            hits.append(term)
    if item.get("source") == "Bloomberg":
        score += 5
    score = max(0, min(score, 96))

    summary = item.get("summary_original", "")
    summary = re.sub(r"\s+", " ", summary).strip()
    if len(summary) > 360:
        summary = summary[:357].rstrip() + "..."
    reason = "Dampak diperkirakan terbatas."
    if score >= 70:
        reason = "Berpotensi berdampak besar pada pasar atau perkembangan teknologi."
    elif score >= 40:
        reason = "Layak diperhatikan karena dapat memengaruhi tren pasar atau teknologi."

    return {
        "title_id": item.get("title_original", ""),
        "summary_id": summary or "Ringkasan belum tersedia dari feed sumber.",
        "importance_score": score,
        "importance_level": level_from_score(score),
        "importance_reason": reason,
    }


def _extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


@lru_cache(maxsize=1)
def get_client():
    if not OpenAI or not os.getenv("OPENAI_API_KEY"):
        return None
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def analyze_with_ai(item):
    client = get_client()
    if client is None:
        return heuristic_analysis(item)

    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    prompt = f"""
Analisis satu berita untuk dashboard investasi, teknologi, blockchain, dan crypto Indonesia.

Aturan:
- Terjemahkan judul ke Bahasa Indonesia yang natural bila judul bukan Bahasa Indonesia.
- Buat ringkasan Bahasa Indonesia maksimal 2 kalimat, hanya berdasarkan teks yang diberikan.
- Jangan mengarang fakta yang tidak ada di input.
- Nilai importance_score 0-100 berdasarkan dampak pasar, dampak teknologi/blockchain, besaran kejadian, urgensi, dan kebaruan.
- Level harus salah satu: normal, attention, important, very-important.
- Reason satu kalimat pendek Bahasa Indonesia.

Sumber: {item.get('source')}
Publisher: {item.get('publisher')}
Kategori: {item.get('category')}
Judul: {item.get('title_original')}
Ringkasan feed: {item.get('summary_original')}

Balas JSON valid saja:
{{
  "title_id": "...",
  "summary_id": "...",
  "importance_score": 0,
  "importance_level": "normal",
  "importance_reason": "..."
}}
""".strip()

    try:
        response = client.responses.create(model=model, input=prompt)
        result = _extract_json(response.output_text)
        score = int(result.get("importance_score", 0))
        score = max(0, min(score, 100))
        return {
            "title_id": str(result.get("title_id") or item.get("title_original", "")),
            "summary_id": str(result.get("summary_id") or item.get("summary_original", "")),
            "importance_score": score,
            "importance_level": level_from_score(score),
            "importance_reason": str(result.get("importance_reason") or ""),
        }
    except Exception as exc:
        fallback = heuristic_analysis(item)
        fallback["importance_reason"] += f" (AI fallback aktif: {type(exc).__name__})"
        return fallback


def analyze_batch(items, batch_size=8):
    """Analyze items in small batches to keep refresh fast and API usage efficient."""
    if not items:
        return []
    client = get_client()
    if client is None:
        return [{**item, **heuristic_analysis(item)} for item in items]

    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    completed = []
    for start in range(0, len(items), batch_size):
        chunk = items[start:start + batch_size]
        compact = [
            {
                "id": i["id"],
                "source": i.get("source"),
                "publisher": i.get("publisher"),
                "category": i.get("category"),
                "title": i.get("title_original"),
                "summary": i.get("summary_original"),
            }
            for i in chunk
        ]
        prompt = """
Kamu adalah news intelligence analyzer investasi, teknologi, blockchain, dan crypto untuk pembaca Indonesia.
Untuk setiap item:
1. Terjemahkan judul ke Bahasa Indonesia natural jika perlu.
2. Ringkas maksimal 2 kalimat dalam Bahasa Indonesia, hanya dari input.
3. Beri importance_score 0-100 berdasarkan dampak pasar, dampak teknologi/blockchain, besaran kejadian, urgensi, dan kebaruan.
4. reason satu kalimat pendek dalam Bahasa Indonesia.
Jangan mengarang fakta di luar input.

Balas JSON valid saja dalam format:
{"items":[{"id":"...","title_id":"...","summary_id":"...","importance_score":0,"importance_reason":"..."}]}

INPUT:
""" + json.dumps(compact, ensure_ascii=False)
        try:
            response = client.responses.create(model=model, input=prompt)
            parsed = _extract_json(response.output_text)
            result_map = {str(x.get("id")): x for x in parsed.get("items", []) if x.get("id")}
            for item in chunk:
                result = result_map.get(item["id"])
                if not result:
                    completed.append({**item, **heuristic_analysis(item)})
                    continue
                score = max(0, min(int(result.get("importance_score", 0)), 100))
                completed.append({
                    **item,
                    "title_id": str(result.get("title_id") or item.get("title_original", "")),
                    "summary_id": str(result.get("summary_id") or item.get("summary_original", "")),
                    "importance_score": score,
                    "importance_level": level_from_score(score),
                    "importance_reason": str(result.get("importance_reason") or ""),
                })
        except Exception:
            completed.extend([{**item, **heuristic_analysis(item)} for item in chunk])
    return completed

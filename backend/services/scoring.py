import re

# Rule-based only. No AI/LLM service is used.
WEIGHTS = {
    # Highest-impact market/regulatory events
    "stock market crash": 40,
    "market crash": 40,
    "bankruptcy": 34,
    "bangkrut": 34,
    "hacking": 32,
    "hack": 28,
    "diretas": 28,
    "exploit": 28,
    "sec": 26,
    "federal reserve": 28,
    "the fed": 25,
    "interest rate": 24,
    "suku bunga": 24,
    "inflation": 22,
    "inflasi": 22,
    "recession": 28,
    "resesi": 28,
    "crypto regulation": 30,
    "blockchain regulation": 30,
    "regulasi kripto": 30,
    "kebijakan pemerintah": 24,
    "government policy": 24,
    "etf": 22,
    "ipo": 24,
    "merger": 25,
    "acquisition": 25,
    "akuisisi": 25,
    "major funding": 24,
    "pendanaan besar": 24,
    # Major assets / companies / sectors
    "bitcoin": 18,
    "btc": 14,
    "ethereum": 18,
    "ether": 14,
    "cryptocurrency exchange": 22,
    "crypto exchange": 22,
    "bursa kripto": 22,
    "semiconductor": 18,
    "semikonduktor": 18,
    "nvidia": 18,
    "microsoft": 14,
    "google": 14,
    "openai": 16,
    "apple": 14,
    "meta": 14,
    "major ai announcement": 25,
    "artificial intelligence": 12,
}

AMPLIFIERS = {
    "surge": 12,
    "soar": 12,
    "plunge": 14,
    "crash": 18,
    "record high": 12,
    "all-time high": 14,
    "anjlok": 14,
    "melonjak": 12,
    "rekor": 10,
    "darurat": 12,
    "ban": 15,
    "larangan": 15,
    "approved": 12,
    "approval": 12,
    "disetujui": 12,
}


def importance_level(score: int) -> str:
    if score >= 85:
        return "SANGAT PENTING"
    if score >= 70:
        return "PENTING"
    if score >= 40:
        return "PERHATIAN"
    return "NORMAL"


def score_importance(title: str, summary: str) -> tuple[int, str]:
    text = f"{title} {summary}".lower()
    score = 8
    hits = 0

    for keyword, weight in WEIGHTS.items():
        if re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text):
            score += weight
            hits += 1

    for keyword, weight in AMPLIFIERS.items():
        if re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text):
            score += weight

    # Multiple relevant signals in one story matter more than one generic keyword.
    if hits >= 3:
        score += 10
    elif hits >= 2:
        score += 5

    score = max(0, min(100, score))
    return score, importance_level(score)

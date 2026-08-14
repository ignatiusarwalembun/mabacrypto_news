import re

RULES = {
    "bitcoin": 14,
    "btc": 10,
    "ethereum": 12,
    "eth": 8,
    "sec": 18,
    "federal reserve": 18,
    "fed rate": 18,
    "interest rate": 15,
    "suku bunga": 15,
    "inflation": 13,
    "inflasi": 13,
    "recession": 18,
    "resesi": 18,
    "stock market crash": 28,
    "market crash": 25,
    "crash": 17,
    "acquisition": 14,
    "akuisisi": 14,
    "merger": 14,
    "bankruptcy": 22,
    "bangkrut": 22,
    "funding": 10,
    "pendanaan": 10,
    "ipo": 12,
    "ai announcement": 18,
    "artificial intelligence": 10,
    "semiconductor": 13,
    "semikonduktor": 13,
    "nvidia": 13,
    "microsoft": 9,
    "google": 8,
    "openai": 12,
    "apple": 8,
    "meta": 8,
    "blockchain regulation": 20,
    "crypto regulation": 20,
    "regulation": 11,
    "regulasi": 11,
    "etf": 13,
    "hack": 18,
    "hacking": 18,
    "peretasan": 18,
    "cryptocurrency exchange": 14,
    "crypto exchange": 14,
    "kebijakan pemerintah": 15,
    "government policy": 15,
}

HIGH_IMPACT_PHRASES = (
    "emergency",
    "darurat",
    "historic",
    "rekor tertinggi",
    "record high",
    "record low",
    "plunges",
    "surges",
    "melonjak",
    "anjlok",
    "runtuh",
    "collapse",
)


def score_importance(title: str, summary: str) -> tuple[int, str]:
    text = f"{title} {summary}".lower()
    score = 6

    for keyword, weight in RULES.items():
        if keyword in text:
            score += weight

    if any(phrase in text for phrase in HIGH_IMPACT_PHRASES):
        score += 14

    percentages = [float(x) for x in re.findall(r"(?<!\d)(\d{1,3}(?:\.\d+)?)\s*%", text)]
    if percentages:
        biggest = max(percentages)
        if biggest >= 20:
            score += 20
        elif biggest >= 10:
            score += 14
        elif biggest >= 5:
            score += 8

    score = max(0, min(100, score))
    if score >= 85:
        level = "SANGAT PENTING"
    elif score >= 70:
        level = "PENTING"
    elif score >= 40:
        level = "PERHATIAN"
    else:
        level = "NORMAL"
    return score, level

import re

IMPORTANT_TERMS = {
    # Macro / markets
    "rate cut": 18, "rate hike": 20, "federal reserve": 16, "fed": 12,
    "bank indonesia": 12, "inflation": 10, "recession": 18, "crash": 25,
    "plunge": 20, "record high": 14, "acquisition": 15, "merger": 15,
    "ipo": 12, "billion": 12, "trillion": 16, "rupiah": 7, "ihsg": 7,
    "tariff": 12, "sanction": 14, "war": 18, "oil": 7, "gold": 7,

    # Technology
    "semiconductor": 12, "chip": 10, "artificial intelligence": 12, "ai": 8,
    "nvidia": 10, "openai": 10, "google": 7, "microsoft": 7, "apple": 7,
    "data center": 10, "robot": 9, "robotics": 10,

    # Blockchain / crypto
    "blockchain": 10, "crypto": 9, "cryptocurrency": 9, "kripto": 9,
    "bitcoin": 12, "ethereum": 11, "stablecoin": 12, "tokenization": 10,
    "tokenisasi": 10, "web3": 8, "etf": 10, "sec": 10,
    "hack": 24, "hacked": 24, "exploit": 22, "breach": 20,
    "liquidation": 16, "liquidations": 16, "bankruptcy": 20,
    "approval": 12, "approved": 12, "ban": 22, "regulation": 14,
}

# Deterministic phrase glossary. This is intentionally local: no LLM, no API key,
# and no request to a translation provider. It improves common finance/tech/crypto
# headlines while preserving unknown words rather than inventing a translation.
PHRASE_TRANSLATIONS = [
    (r"\brecord high\b", "rekor tertinggi"),
    (r"\brate cut\b", "pemangkasan suku bunga"),
    (r"\brate hike\b", "kenaikan suku bunga"),
    (r"\binterest rates?\b", "suku bunga"),
    (r"\bfederal reserve\b", "Federal Reserve"),
    (r"\bstock market\b", "pasar saham"),
    (r"\bstocks\b", "saham"),
    (r"\bshares\b", "saham"),
    (r"\bbonds\b", "obligasi"),
    (r"\binvestors\b", "investor"),
    (r"\binvestment\b", "investasi"),
    (r"\bmarkets\b", "pasar"),
    (r"\bmarket\b", "pasar"),
    (r"\beconomy\b", "ekonomi"),
    (r"\binflation\b", "inflasi"),
    (r"\brecession\b", "resesi"),
    (r"\bacquisition\b", "akuisisi"),
    (r"\bmerger\b", "merger"),
    (r"\bsemiconductor\b", "semikonduktor"),
    (r"\bartificial intelligence\b", "kecerdasan buatan"),
    (r"\bdata center\b", "pusat data"),
    (r"\bcloud computing\b", "komputasi cloud"),
    (r"\brobotics\b", "robotika"),
    (r"\bstartup\b", "startup"),
    (r"\bblockchain\b", "blockchain"),
    (r"\bcryptocurrency\b", "kripto"),
    (r"\bcrypto\b", "kripto"),
    (r"\bstablecoin\b", "stablecoin"),
    (r"\btokenization\b", "tokenisasi"),
    (r"\bregulation\b", "regulasi"),
    (r"\bregulator\b", "regulator"),
    (r"\bapproval\b", "persetujuan"),
    (r"\bapproved\b", "disetujui"),
    (r"\bban\b", "pelarangan"),
    (r"\bhack(?:ed)?\b", "diretas"),
    (r"\bexploit\b", "eksploitasi celah"),
    (r"\bliquidations?\b", "likuidasi"),
    (r"\bbankruptcy\b", "kebangkrutan"),
    (r"\brises?\b", "naik"),
    (r"\bgains?\b", "menguat"),
    (r"\bsurges?\b", "melonjak"),
    (r"\bjumps?\b", "melonjak"),
    (r"\bfalls?\b", "turun"),
    (r"\bdrops?\b", "turun"),
    (r"\bslumps?\b", "merosot"),
    (r"\bplunges?\b", "anjlok"),
    (r"\blaunches?\b", "meluncurkan"),
    (r"\bannounces?\b", "mengumumkan"),
    (r"\breports?\b", "melaporkan"),
]


def level_from_score(score):
    if score >= 85:
        return "very-important"
    if score >= 70:
        return "important"
    if score >= 40:
        return "attention"
    return "normal"


def local_translate(text):
    """Best-effort local glossary translation without AI or external services."""
    if not text:
        return ""
    translated = re.sub(r"\s+", " ", text).strip()
    for pattern, replacement in PHRASE_TRANSLATIONS:
        translated = re.sub(pattern, replacement, translated, flags=re.IGNORECASE)
    return translated


def compact_summary(text, max_chars=360):
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return "Ringkasan belum tersedia dari feed sumber."
    # Remove common Google News tail noise where possible.
    text = re.sub(r"\s+View Full Coverage on Google News\.?$", "", text, flags=re.I)
    if len(text) > max_chars:
        text = text[: max_chars - 3].rstrip(" ,.;:-") + "..."
    return local_translate(text)


def heuristic_analysis(item):
    text = f"{item.get('title_original', '')} {item.get('summary_original', '')}".lower()
    score = 18
    hits = []

    for term, value in IMPORTANT_TERMS.items():
        if term in text:
            score += value
            hits.append(term)

    # Source weighting is deliberately small; importance comes mainly from content.
    if item.get("source") == "Bloomberg":
        score += 4

    # Large numeric moves often matter for market dashboards.
    if re.search(r"\b(?:[1-9]\d?|100)(?:\.\d+)?%\b", text):
        score += 12
    if re.search(r"\$\s?\d+(?:\.\d+)?\s?(?:billion|trillion|bn|tn)\b", text):
        score += 14

    score = max(0, min(score, 96))

    if score >= 85:
        reason = "Sangat penting karena memuat sinyal berdampak besar pada pasar, teknologi, atau ekosistem blockchain/crypto."
    elif score >= 70:
        reason = "Berpotensi berdampak besar pada pasar, teknologi, atau blockchain/crypto."
    elif score >= 40:
        reason = "Layak diperhatikan karena memuat sinyal yang dapat memengaruhi tren pasar atau teknologi."
    else:
        reason = "Dampak yang terdeteksi dari headline dan feed relatif terbatas."

    return {
        "title_id": local_translate(item.get("title_original", "")),
        "summary_id": compact_summary(item.get("summary_original", "")),
        "importance_score": score,
        "importance_level": level_from_score(score),
        "importance_reason": reason,
    }


def analyze_batch(items, batch_size=8):
    """Analyze locally. batch_size is kept for API compatibility with the refresher."""
    return [{**item, **heuristic_analysis(item)} for item in items]

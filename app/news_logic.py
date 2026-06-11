import re
from collections import Counter
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PREFIXES = ("utm_",)
TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "ref", "s", "campaign"}
STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "over", "after", "before",
    "news", "says", "said", "more", "will", "amid", "while", "about", "have", "has",
    "cointelegraph", "coindesk", "block", "reuters", "bloomberg", "cnbc", "newbtc",
}
KNOWN_TERMS = [
    "Michael Saylor", "Tom Lee", "Satoshi Nakamoto", "Satoshi", "Strategy", "MicroStrategy",
    "Bitcoin", "Ethereum", "Solana", "XRP", "BNB", "ETF", "SEC", "CFTC", "Federal Reserve",
    "BlackRock", "Coinbase", "Binance", "Tether", "Circle", "Stablecoin", "Treasury",
]


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    parts = urlsplit(url)
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    query_pairs = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        k = key.lower()
        if k.startswith(TRACKING_PREFIXES) or k in TRACKING_PARAMS:
            continue
        query_pairs.append((key, value))
    query = urlencode(query_pairs, doseq=True)
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((scheme, netloc, path, query, ""))


def _title_case_token(token: str) -> str:
    return " ".join(part[:1].upper() + part[1:] for part in token.split())


def extract_keywords(text: str, limit: int = 5) -> list[str]:
    text = text or ""
    lowered = text.lower()
    candidates: list[str] = []
    for term in KNOWN_TERMS:
        if term.lower() in lowered:
            candidates.append(term)

    # Capture person/org-like phrases: Michael Saylor, Tom Lee, Federal Reserve.
    phrase_pattern = re.compile(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3}\b")
    for match in phrase_pattern.findall(text):
        if match.lower() not in STOPWORDS and match not in candidates:
            candidates.append(match)

    words = re.findall(r"\b[A-Za-z][A-Za-z0-9-]{2,}\b", text)
    counts = Counter(
        _title_case_token(w)
        for w in words
        if w.lower() not in STOPWORDS and not w.isdigit()
    )
    for word, _count in counts.most_common():
        if word not in candidates and not any(word in phrase.split() for phrase in candidates):
            candidates.append(word)
        if len(candidates) >= limit:
            break
    return candidates[:limit]


def detect_duplicates(url: str, title: str, keywords: list[str], existing_articles: list[dict], target_date: str) -> list[dict]:
    normalized = normalize_url(url)
    new_keywords = {k.lower(): k for k in (keywords or [])}
    duplicates = []
    for article in existing_articles:
        if article.get("created_date") != target_date:
            continue
        article_url = normalize_url(article.get("url", ""))
        if article_url == normalized:
            duplicates.append({"type": "url", "article": article, "overlap": []})
            continue
        old_keywords = {k.lower(): k for k in (article.get("keywords") or [])}
        overlap_lc = [k for k in new_keywords if k in old_keywords]
        if len(overlap_lc) >= 2:
            duplicates.append({
                "type": "keyword",
                "article": article,
                "overlap": [new_keywords[k] for k in overlap_lc],
            })
    return duplicates

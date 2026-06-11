from datetime import date

from app.news_logic import extract_keywords, normalize_url, detect_duplicates


def test_extract_keywords_returns_people_and_entities_before_generic_terms():
    text = "Michael Saylor says Strategy bought Bitcoin while Tom Lee comments on Ethereum ETF."

    keywords = extract_keywords(text, limit=5)

    assert "Michael Saylor" in keywords
    assert "Strategy" in keywords
    assert "Tom Lee" in keywords
    assert "Bitcoin" in keywords
    assert keywords.index("Michael Saylor") < keywords.index("Bitcoin")


def test_normalize_url_removes_tracking_and_trailing_slash():
    url = "https://example.com/news/story/?utm_source=x&utm_campaign=y&ref=abc&id=123"

    assert normalize_url(url) == "https://example.com/news/story?id=123"


def test_detect_duplicates_finds_url_and_keyword_overlap_for_same_day():
    today = date(2026, 6, 11).isoformat()
    existing = [
        {
            "id": 1,
            "url": "https://cointelegraph.com/news/strategy-buys-bitcoin",
            "title": "Strategy buys more Bitcoin as Michael Saylor signals confidence",
            "keywords": ["Michael Saylor", "Strategy", "Bitcoin"],
            "created_date": today,
            "journalist": "A",
        },
        {
            "id": 2,
            "url": "https://www.theblock.co/post/eth-etf",
            "title": "Ethereum ETF inflows rise",
            "keywords": ["Ethereum", "ETF"],
            "created_date": today,
            "journalist": "B",
        },
    ]

    url_hit = detect_duplicates(
        "https://cointelegraph.com/news/strategy-buys-bitcoin?utm_source=twitter",
        "Different title",
        ["Macro"],
        existing,
        today,
    )
    keyword_hit = detect_duplicates(
        "https://coindesk.com/markets/saylor-strategy-bitcoin",
        "Saylor and Strategy add Bitcoin exposure",
        ["Michael Saylor", "Strategy", "Bitcoin"],
        existing,
        today,
    )

    assert url_hit[0]["type"] == "url"
    assert keyword_hit[0]["type"] == "keyword"
    assert keyword_hit[0]["overlap"] == ["Michael Saylor", "Strategy", "Bitcoin"]

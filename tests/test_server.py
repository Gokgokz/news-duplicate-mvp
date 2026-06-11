from app.server import create_app


def test_submit_links_creates_articles_and_reports_duplicates(tmp_path):
    db_path = tmp_path / "news.db"
    app = create_app({"DATABASE": str(db_path), "TESTING": True})
    client = app.test_client()

    first = client.post("/api/links", json={
        "journalist": "A",
        "links": ["https://cointelegraph.com/news/strategy-buys-bitcoin"],
    })
    assert first.status_code == 200
    first_payload = first.get_json()
    assert first_payload["created"] == 1
    assert first_payload["duplicates"] == []
    assert first_payload["articles"][0]["keywords"]

    second = client.post("/api/links", json={
        "journalist": "B",
        "links": ["https://cointelegraph.com/news/strategy-buys-bitcoin?utm_source=x"],
    })
    second_payload = second.get_json()
    assert second_payload["created"] == 0
    assert second_payload["duplicates"][0]["type"] == "url"


def test_today_endpoint_returns_keyword_summary(tmp_path):
    db_path = tmp_path / "news.db"
    app = create_app({"DATABASE": str(db_path), "TESTING": True})
    client = app.test_client()

    client.post("/api/links", json={
        "journalist": "A",
        "links": [
            "https://example.com/michael-saylor-strategy-bitcoin",
            "https://example.com/tom-lee-ethereum-etf",
        ],
    })

    payload = client.get("/api/today").get_json()

    assert len(payload["articles"]) == 2
    keyword_names = [row["keyword"] for row in payload["keywords"]]
    assert "Michael Saylor" in keyword_names or "Saylor" in keyword_names
    assert "Tom Lee" in keyword_names

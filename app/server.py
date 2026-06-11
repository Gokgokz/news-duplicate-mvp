import json
import os
import re
import sqlite3
from datetime import datetime
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup
from flask import Flask, g, jsonify, render_template, request

from app.news_logic import detect_duplicates, extract_keywords, normalize_url

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    normalized_url TEXT NOT NULL,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    journalist TEXT NOT NULL,
    keywords TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_date TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(created_date);
CREATE INDEX IF NOT EXISTS idx_articles_normalized_url ON articles(normalized_url);
"""


def create_app(config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(
        DATABASE=os.environ.get("NEWS_DB", os.path.join(os.getcwd(), "news.db")),
        TESTING=False,
    )
    if config:
        app.config.update(config)

    @app.before_request
    def _ensure_db():
        init_db()

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/today")
    def api_today():
        target_date = request.args.get("date") or datetime.now().date().isoformat()
        articles = list_articles(target_date)
        return jsonify({"date": target_date, "articles": articles, "keywords": keyword_summary(articles)})

    @app.post("/api/links")
    def api_links():
        payload = request.get_json(force=True) or {}
        journalist = (payload.get("journalist") or "ไม่ระบุชื่อ").strip()
        raw_links = payload.get("links") or []
        if isinstance(raw_links, str):
            raw_links = [line.strip() for line in raw_links.splitlines() if line.strip()]
        target_date = payload.get("date") or datetime.now().date().isoformat()
        existing = list_articles(target_date)
        created_articles = []
        duplicates = []
        for url in raw_links:
            metadata = fetch_metadata(url, testing=app.config["TESTING"])
            keywords = extract_keywords(f"{metadata['title']} {metadata['source']} {metadata['url']}", limit=5)
            hits = detect_duplicates(metadata["url"], metadata["title"], keywords, existing + created_articles, target_date)
            if hits:
                duplicates.append({
                    "url": url,
                    "title": metadata["title"],
                    "keywords": keywords,
                    "type": hits[0]["type"],
                    "matches": hits,
                })
                continue
            article = insert_article(metadata, journalist, keywords, target_date)
            created_articles.append(article)
        return jsonify({"created": len(created_articles), "articles": created_articles, "duplicates": duplicates})

    return app


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app_database())
        g.db.row_factory = sqlite3.Row
    return g.db


def current_app_database():
    from flask import current_app
    return current_app.config["DATABASE"]


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()


def source_from_url(url: str) -> str:
    host = urlsplit(url).netloc.lower().removeprefix("www.")
    return host or "unknown"


def title_from_slug(url: str) -> str:
    path = urlsplit(url).path.strip("/")
    slug = path.split("/")[-1] if path else source_from_url(url)
    slug = re.sub(r"[-_]+", " ", slug)
    return slug.strip().title() or url


def fetch_metadata(url: str, testing: bool = False) -> dict:
    normalized = normalize_url(url)
    source = source_from_url(normalized)
    title = title_from_slug(normalized)
    if not testing:
        try:
            response = requests.get(normalized, timeout=8, headers={"User-Agent": "NewsDuplicateMVP/1.0"})
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            og_title = soup.select_one('meta[property="og:title"], meta[name="twitter:title"]')
            html_title = soup.find("title")
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
            elif html_title and html_title.text:
                title = html_title.text.strip()
        except Exception:
            pass
    return {"url": url.strip(), "normalized_url": normalized, "source": source, "title": title}


def row_to_article(row) -> dict:
    return {
        "id": row["id"],
        "url": row["url"],
        "normalized_url": row["normalized_url"],
        "title": row["title"],
        "source": row["source"],
        "journalist": row["journalist"],
        "keywords": json.loads(row["keywords"]),
        "created_at": row["created_at"],
        "created_date": row["created_date"],
    }


def list_articles(target_date: str) -> list[dict]:
    rows = get_db().execute(
        "SELECT * FROM articles WHERE created_date = ? ORDER BY created_at DESC, id DESC",
        (target_date,),
    ).fetchall()
    return [row_to_article(row) for row in rows]


def insert_article(metadata: dict, journalist: str, keywords: list[str], target_date: str) -> dict:
    now = datetime.now().isoformat(timespec="seconds")
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO articles (url, normalized_url, title, source, journalist, keywords, created_at, created_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            metadata["url"], metadata["normalized_url"], metadata["title"], metadata["source"],
            journalist, json.dumps(keywords, ensure_ascii=False), now, target_date,
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM articles WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_article(row)


def keyword_summary(articles: list[dict]) -> list[dict]:
    counts = {}
    for article in articles:
        for keyword in article.get("keywords", []):
            counts.setdefault(keyword, {"keyword": keyword, "count": 0, "articles": []})
            counts[keyword]["count"] += 1
            counts[keyword]["articles"].append(article["id"])
    return sorted(counts.values(), key=lambda row: (-row["count"], row["keyword"]))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    create_app().run(host="0.0.0.0", port=port, debug=True)

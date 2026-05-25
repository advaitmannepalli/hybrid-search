from fastapi.testclient import TestClient
from unittest.mock import patch

with patch("opensearchpy.OpenSearch"), patch("sentence_transformers.SentenceTransformer"):
    from main import app

client = TestClient(app)


def fake_hit(score, title, url, body):
    return {"_score": score, "_source": {"title": title, "url": url, "body": body}}


def test_search_returns_results():
    import main

    main.model.encode.return_value.tolist.return_value = [0.1] * 384
    main.client.search.return_value = {
        "hits": {"hits": [fake_hit(5.0, "Test", "https://example.com", "body")]}
    }

    resp = client.get("/search?q=hello")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["title"] == "Test"


def test_search_empty_query_returns_422():
    resp = client.get("/search")
    assert resp.status_code == 422


def test_search_dedup_by_url():
    import main

    main.model.encode.return_value.tolist.return_value = [0.1] * 384
    main.client.search.return_value = {
        "hits": {
            "hits": [
                fake_hit(4.0, "Low", "https://example.com/page", "body low"),
                fake_hit(5.0, "High", "https://example.com/page/", "body high"),
            ]
        }
    }

    resp = client.get("/search?q=test")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["title"] == "High"


def test_search_max_ten_results():
    import main

    main.model.encode.return_value.tolist.return_value = [0.1] * 384
    hits = [
        fake_hit(float(i), f"Page {i}", f"https://example.com/{i}", f"body {i}")
        for i in range(20)
    ]
    main.client.search.return_value = {"hits": {"hits": hits}}

    resp = client.get("/search?q=test")
    data = resp.json()
    assert len(data["results"]) <= 10


def test_search_response_shape():
    import main

    main.model.encode.return_value.tolist.return_value = [0.1] * 384
    main.client.search.return_value = {
        "hits": {
            "hits": [
                fake_hit(3.5, "Title", "https://example.com/page", "Some body text")
            ]
        }
    }

    resp = client.get("/search?q=hello")
    item = resp.json()["results"][0]
    assert set(item.keys()) == {"score", "title", "url", "body"}
    assert isinstance(item["score"], float)
    assert isinstance(item["title"], str)
    assert isinstance(item["url"], str)
    assert isinstance(item["body"], str)

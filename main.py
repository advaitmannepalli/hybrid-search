from urllib.parse import urlparse
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from opensearchpy import OpenSearch
from sentence_transformers import SentenceTransformer

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
client = OpenSearch(hosts=["http://localhost:9200"])
model = SentenceTransformer("all-MiniLM-L6-v2")

@app.get("/search")
def search(q: str = Query(...)):

    # generate vector for the query
    query_vector = model.encode(q).tolist()

    # normalise URL so trailing-slash variants count as the same page
    def normalise_url(u):
        p = urlparse(u)
        return f"{p.scheme}://{p.netloc}{p.path.rstrip('/')}"

    # run both searches in parallel
    response = client.search(
        index="docs",
        body={
            "size": 25,
            "query": {
                "bool": {
                    "should": [
                        # BM25 keyword search
                        {
                            "multi_match": {
                                "query": q,
                                "fields": ["title^2", "body"],
                                "boost": 0.5
                            }
                        },
                        # vector semantic search
                        {
                            "knn": {
                                "embedding": {
                                    "vector": query_vector,
                                    "k": 10,
                                    "boost": 0.5
                                }
                            }
                        }
                    ]
                }
            }
        }
    )

    best = {}
    for h in response["hits"]["hits"]:
        key = normalise_url(h["_source"]["url"])
        score = h["_score"]
        if key not in best or score > best[key]["score"]:
            best[key] = {
                "score": score,
                "title": h["_source"]["title"],
                "url":   h["_source"]["url"],
                "body":  h["_source"]["body"]
            }

    results = sorted(best.values(), key=lambda r: r["score"], reverse=True)[:10]
    return {"results": results}
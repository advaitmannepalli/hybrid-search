from fastapi import FastAPI, Query
from opensearchpy import OpenSearch
from sentence_transformers import SentenceTransformer

app = FastAPI()
client = OpenSearch(hosts=["http://localhost:9200"])
model = SentenceTransformer("all-MiniLM-L6-v2")

@app.get("/search")
def search(q: str = Query(...)):

    # generate vector for the query
    query_vector = model.encode(q).tolist()

    # run both searches in parallel
    response = client.search(
        index="docs",
        body={
            "size": 10,
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

    hits = [
        {
            "score": h["_score"],
            "title": h["_source"]["title"],
            "url":   h["_source"]["url"],
            "body":  h["_source"]["body"]
        }
        for h in response["hits"]["hits"]
    ]

    return {"results": hits}
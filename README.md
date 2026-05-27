# Hybrid Search

Crawls a website, chunks up all the documents, and indexes them for hybrid search. Combines BM25 keyword search with vector embeddings so you actually find what you're looking for. FastAPI backend, React frontend, OpenSearch under the hood.

## How it works

1. **Crawl** — starts at a URL, follows links, downloads pages, PDFs, DOCX, and XLSX files
2. **Chunk** — splits each document into overlapping 300-word segments
3. **Embed** — converts each chunk into a 384-dimensional vector using sentence-transformers
4. **Index** — stores everything in OpenSearch with k-NN enabled
5. **Search** — runs BM25 keyword search and k-NN vector search together, returns the best results

## Prerequisites

- Docker
- Python 3.14+
- Node.js
- `venv/` already set up (if not, run `python3 -m venv venv` and `source venv/bin/activate && pip install -r requirements.txt`)

## Quick start

```bash
# 1. Start OpenSearch
docker-compose up -d

# 2. Check it's running
docker ps

# 3. Activate the environment and crawl/index
source venv/bin/activate
python ingest.py

# 4. Start the API
uvicorn main:app --reload

# 5. In another terminal, start the frontend
cd frontend && npm install && npm run dev
```

Open `http://localhost:5173` and search.

**Note:** `ingest.py` downloads and indexes up to 500 pages. It takes a while. If you want to change the target site or page limit, edit `START_URL` and `MAX_PAGES` at the top of `ingest.py`.

## API

```
GET /search?q=<query>
```

Returns JSON:

```json
{
  "results": [
    {
      "score": 5.45,
      "title": "Page title (part 1)",
      "url": "https://example.com/page",
      "body": "First 300 words of the relevant chunk..."
    }
  ]
}
```

## Project structure

```
├── docker-compose.yml    # OpenSearch 2.11
├── ingest.py             # Crawler + indexer (producer-consumer with 3 embedder threads)
├── main.py               # FastAPI search server
├── requirements.txt      # Python dependencies (includes test deps)
├── test_main.py          # 5 API tests (mock OpenSearch + model)
├── test_ingest.py        # 8 chunking + link-parsing tests
└── frontend/             # Vite + React app
    ├── public/fonts/     # Self-hosted Star Jedi TTF (Boba Fonts)
    ├── src/App.jsx       # Search UI
    └── src/App.css       # Dark theme, CSS animations, Star Jedi font
```

## Troubleshooting

**OpenSearch won't start** — Docker needs at least 4GB of memory allocated. Check Docker Desktop settings.

**Search returns nothing** — Make sure you ran `python ingest.py` first and it finished without errors.

**Frontend can't reach the API** — The Vite dev server proxies `/api` to `localhost:8000`. Make sure `uvicorn main:app --reload` is running.

**404 on search from the frontend** — The proxy rewrites `/api/search` to `/search`. If you changed the backend route, update `vite.config.js`.

# API Application

FastAPI service providing the RAG query endpoints.

## Planned Structure

```
app/
├── main.py              # FastAPI application entry
├── routes/              # API route handlers
│   ├── query.py         # /query endpoint (SSE streaming)
│   ├── collections.py   # /collections, /sources endpoints
│   └── health.py        # /healthz
├── retrieval/           # Hybrid retrieval (lexical + vector + RRF + rerank)
├── llm/                 # Provider-agnostic LLM layer (Bedrock + fallback)
├── composer/            # Response generation with licence enforcement
├── guards/              # Rate limiting, budget caps, input validation
└── Dockerfile
```

## Key Features (Phase 2+)

- Hybrid retrieval: lexical (Postgres FTS) + vector (pgvector HNSW) + RRF fusion + reranker
- Licence-aware response composer (Class A/B/C enforcement)
- SSE streaming responses
- Per-IP rate limits and global daily spend cap
- Langfuse tracing on every request

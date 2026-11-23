# Phase 1 architecture (RAG core)

Phase 1 delivers ingest → pgvector → hybrid retrieval → Bedrock answer → eval gates. No public API, ALB, UI, or Langfuse yet.

```mermaid
flowchart LR
  subgraph ingest_flow [Ingest Fargate task public subnet]
    Fetch[Fetchers arXiv HTML PDF]
    Chunk[Chunker]
    Emb[Titan Embeddings V2 1024-d]
    Fetch --> Chunk --> Emb
  end

  subgraph data [RDS private subnet]
    PG[(Postgres 16 + pgvector)]
  end

  subgraph core [Python library app/core]
    RRF[RRF hybrid retrieval]
    LLM[Claude Haiku Converse]
    Lic[Licence composer]
    RRF --> LLM --> Lic
  end

  Emb --> PG
  PG --> RRF
  LLM --> Bedrock[Bedrock eu-west-2]
  Emb --> Bedrock
```

## Embeddings

Default embedding model: `amazon.titan-embed-text-v2:0` (1024 dimensions). Documented on [Amazon Bedrock model list](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html) for European regions; verify in-account while AWS seller verification completes. Fallback in code: set `RAG_EMBEDDING_MODEL_ID=cohere.embed-english-v3` (not default).
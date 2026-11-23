CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    collection TEXT NOT NULL,
    title TEXT NOT NULL,
    authors TEXT[] NOT NULL DEFAULT '{}',
    year INT,
    source_url TEXT NOT NULL,
    licence TEXT NOT NULL,
    licence_url TEXT NOT NULL,
    licence_class CHAR(1) NOT NULL CHECK (licence_class IN ('A', 'B', 'C')),
    nc_flag BOOLEAN NOT NULL DEFAULT FALSE,
    nd_flag BOOLEAN NOT NULL DEFAULT FALSE,
    attribution_text TEXT NOT NULL,
    format TEXT NOT NULL,
  content_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
    document_id BIGSERIAL PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
    collection TEXT NOT NULL,
    normalised_text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_id, content_hash)
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id BIGSERIAL PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
    document_id BIGINT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    collection TEXT NOT NULL,
    chunk_index INT NOT NULL,
    section_path TEXT,
    text TEXT NOT NULL,
    token_count INT NOT NULL,
    chunk_hash TEXT NOT NULL,
    embedding vector(1024),
    embedding_model TEXT NOT NULL,
    tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_id, chunk_hash)
);

CREATE INDEX IF NOT EXISTS chunks_collection_idx ON chunks(collection);
CREATE INDEX IF NOT EXISTS chunks_source_idx ON chunks(source_id);
CREATE INDEX IF NOT EXISTS chunks_tsv_gin ON chunks USING GIN (tsv);
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops);
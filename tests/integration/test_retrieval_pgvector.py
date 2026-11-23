from __future__ import annotations

import os
from unittest.mock import patch

import psycopg
import pytest
from pgvector.psycopg import register_vector

from app.core.retrieval import HybridRetriever
from ingest.embed import to_vector
from ingest.migrations.runner import run_migrations


def _dsn() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://rag:raglocal@localhost:5432/ragplatform",
    )


@pytest.fixture(scope="module")
def seeded_db():
    dsn = _dsn()
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
    except psycopg.OperationalError:
        pytest.skip("Postgres/pgvector not available (set DATABASE_URL or start docker compose)")
    run_migrations(dsn)
    doc_vec = to_vector([0.99] + [0.0] * 1023)
    with psycopg.connect(dsn) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sources (
                    source_id, collection, title, authors, source_url,
                    licence, licence_url, licence_class, nc_flag, nd_flag,
                    attribution_text, format, content_hash
                ) VALUES (
                    'cs-test', 'complex-systems', 'Test', ARRAY['T'],
                    'https://example.com', 'CC-BY-4.0', 'https://example.com/l',
                    'A', false, false, 'Test', 'fixture', 'hash-doc'
                ) ON CONFLICT (source_id) DO NOTHING
                """
            )
            cur.execute(
                """
                INSERT INTO documents (source_id, collection, normalised_text, content_hash)
                VALUES ('cs-test', 'complex-systems', 'body', 'hash-doc')
                ON CONFLICT (source_id, content_hash) DO NOTHING
                RETURNING document_id
                """
            )
            row = cur.fetchone()
            if row:
                doc_id = row[0]
            else:
                cur.execute("SELECT document_id FROM documents WHERE source_id='cs-test' LIMIT 1")
                doc_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO chunks (
                    source_id, document_id, collection, chunk_index, section_path,
                    text, token_count, chunk_hash, embedding, embedding_model
                ) VALUES (
                    'cs-test', %s, 'complex-systems', 0, 's',
                    'critical transitions early warning', 5, 'hash-chunk', %s, 'test'
                )
                ON CONFLICT (source_id, chunk_hash) DO UPDATE
                SET embedding = EXCLUDED.embedding, text = EXCLUDED.text
                """,
                (doc_id, doc_vec),
            )
        conn.commit()
    yield dsn


def test_vector_distance_query(seeded_db):
    dsn = seeded_db
    with psycopg.connect(dsn) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            q = to_vector([1.0] + [0.0] * 1023)
            cur.execute(
                """
                SELECT chunk_id FROM chunks
                WHERE collection = %s
                ORDER BY embedding <=> %s
                LIMIT 1
                """,
                ("complex-systems", q),
            )
            assert cur.fetchone() is not None


@patch("app.core.retrieval.embed_texts", return_value=[[1.0] + [0.0] * 1023])
def test_hybrid_retriever_vector_leg(mock_embed, seeded_db):
    retriever = HybridRetriever(seeded_db)
    chunks = retriever.retrieve(
        "early warning",
        collection="complex-systems",
        top_lexical=10,
        top_vector=10,
        top_fused=5,
    )
    assert chunks
    mock_embed.assert_called_once()

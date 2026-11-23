#!/usr/bin/env python3
"""Seed pgvector with a tiny corpus for CI (class A/B + short C excerpts)."""

from __future__ import annotations

import os

import psycopg
from pgvector.psycopg import register_vector

from ingest.migrations.runner import run_migrations

FIXTURES = [
    (
        "cs-018",
        "A",
        "Early warning signals include rising autocorrelation and variance before transitions.",
    ),
    (
        "cs-033",
        "A",
        "Time-average growth under non-ergodicity conflicts with ensemble expected utility.",
    ),
    ("cs-044", "A", "Large language models show emergent benchmark capabilities with scale."),
    ("cs-003", "B", "Agent-based models use local rules producing global patterns."),
    ("cs-021", "B", "Network Science chapters use Creative Commons BY-NC-SA 2.0."),
    ("cs-041", "B", "Think Complexity covers small-world graphs with clustering."),
    ("cs-001", "C", "Newman's survey overview of complex systems (excerpt)."),
]


def main() -> None:
    dsn = os.environ.get("DATABASE_URL", "postgresql://rag:raglocal@localhost:5432/ragplatform")
    run_migrations(dsn)
    vec = [0.01] * 1024
    with psycopg.connect(dsn) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            for sid, licence_class, text in FIXTURES:
                cur.execute(
                    """
                    INSERT INTO sources (
                        source_id, collection, title, authors, source_url,
                        licence, licence_url, licence_class, nc_flag, nd_flag,
                        attribution_text, format, content_hash
                    ) VALUES (
                        %s, 'complex-systems', %s, ARRAY['Fixture'], %s,
                        'TEST', 'https://example.com/licence', %s, false, false,
                        %s, 'fixture', %s
                    ) ON CONFLICT (source_id) DO NOTHING
                    """,
                    (sid, f"Fixture {sid}", f"https://example.com/{sid}", licence_class, sid, sid),
                )
                cur.execute(
                    """
                    INSERT INTO documents (source_id, collection, normalised_text, content_hash)
                    VALUES (%s, 'complex-systems', %s, %s)
                    ON CONFLICT (source_id, content_hash) DO NOTHING
                    RETURNING document_id
                    """,
                    (sid, text, sid),
                )
                row = cur.fetchone()
                if not row:
                    cur.execute(
                        "SELECT document_id FROM documents WHERE source_id=%s LIMIT 1",
                        (sid,),
                    )
                    row = cur.fetchone()
                doc_id = row[0]
                cur.execute(
                    """
                    INSERT INTO chunks (
                        source_id, document_id, collection, chunk_index, section_path,
                        text, token_count, chunk_hash, embedding, embedding_model
                    ) VALUES (
                        %s, %s, 'complex-systems', 0, 'fixture', %s, 20, %s, %s, 'fixture'
                    ) ON CONFLICT (source_id, chunk_hash) DO NOTHING
                    """,
                    (sid, doc_id, text, f"hash-{sid}", vec),
                )
        conn.commit()


if __name__ == "__main__":
    main()

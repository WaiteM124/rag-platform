from __future__ import annotations

import logging
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector

from ingest.chunking import chunk_markdown, content_hash
from ingest.config import CACHE_DIR, db_dsn
from ingest.embed import DEFAULT_MODEL, embed_texts, to_vector
from ingest.fetchers.router import fetch_source_markdown
from ingest.licence import SourceRecord, load_sources
from ingest.migrations.runner import run_migrations

logger = logging.getLogger(__name__)


def ingest_collection(
    collection: str,
    *,
    sources_path: Path,
    limit: int | None = None,
) -> int:
    run_migrations(db_dsn())
    sources = load_sources(str(sources_path))
    if limit is not None:
        sources = sources[:limit]
    cache = Path(CACHE_DIR)
    cache.mkdir(parents=True, exist_ok=True)
    processed = 0
    with psycopg.connect(db_dsn()) as conn:
        register_vector(conn)
        for src in sources:
            try:
                _ingest_one(conn, src, collection, cache)
                processed += 1
            except Exception:
                logger.exception("Failed ingest for %s", src.id)
                raise
        conn.commit()
    return processed


def _ingest_one(
    conn: psycopg.Connection,
    src: SourceRecord,
    collection: str,
    cache: Path,
) -> None:
    cache_file = cache / f"{src.id}.md"
    if cache_file.exists():
        markdown = cache_file.read_text(encoding="utf-8")
    else:
        markdown = fetch_source_markdown(src)
        cache_file.write_text(markdown, encoding="utf-8")
    doc_hash = content_hash(markdown)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sources (
                source_id, collection, title, authors, year, source_url,
                licence, licence_url, licence_class, nc_flag, nd_flag,
                attribution_text, format, content_hash, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, now()
            )
            ON CONFLICT (source_id) DO UPDATE SET
                content_hash = EXCLUDED.content_hash,
                updated_at = now()
            RETURNING content_hash
            """,
            (
                src.id,
                collection,
                src.title,
                src.authors,
                src.year,
                src.url,
                src.licence,
                src.licence_url,
                src.licence_class,
                src.nc_flag,
                src.nd_flag,
                src.attribution_text,
                src.format,
                doc_hash,
            ),
        )
        prev = cur.fetchone()
        if prev and prev[0] == doc_hash:
            logger.info("Unchanged %s, skipping chunks", src.id)
            return
        cur.execute(
            """
            INSERT INTO documents (source_id, collection, normalised_text, content_hash)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (source_id, content_hash) DO UPDATE
            SET normalised_text = EXCLUDED.normalised_text
            RETURNING document_id
            """,
            (src.id, collection, markdown, doc_hash),
        )
        document_id = cur.fetchone()[0]
        chunks = chunk_markdown(markdown)
        if not chunks:
            return
        texts = [c.text for c in chunks]
        vectors = embed_texts(texts)
        for c, vec in zip(chunks, vectors, strict=True):
            cur.execute(
                """
                INSERT INTO chunks (
                    source_id, document_id, collection, chunk_index, section_path,
                    text, token_count, chunk_hash, embedding, embedding_model
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_id, chunk_hash) DO NOTHING
                """,
                (
                    src.id,
                    document_id,
                    collection,
                    c.chunk_index,
                    c.section_path,
                    c.text,
                    c.token_count,
                    c.chunk_hash,
                    to_vector(vec),
                    DEFAULT_MODEL,
                ),
            )

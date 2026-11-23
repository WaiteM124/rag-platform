from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import psycopg
from pgvector.psycopg import register_vector

from ingest.chunking import chunk_markdown, content_hash
from ingest.config import CACHE_DIR, db_dsn
from ingest.embed import (
    DEFAULT_MODEL,
    EmbeddingThrottledError,
    embed_texts,
    get_embed_stats,
    to_vector,
)
from ingest.fetchers.router import fetch_source_markdown
from ingest.licence import SourceRecord, load_sources
from ingest.migrations.runner import run_migrations
from ingest.normalise import normalise_text

logger = logging.getLogger(__name__)


@dataclass
class IngestSummary:
    ok: int = 0
    unchanged: int = 0
    failed: int = 0
    chunks_added: int = 0
    db_sources: int = 0
    db_documents: int = 0
    db_chunks: int = 0
    failed_ids: list[str] = field(default_factory=list)
    embed_calls: int = 0
    throttle_retries: int = 0

    @property
    def attempted(self) -> int:
        return self.ok + self.unchanged + self.failed

    def exit_code(self) -> int:
        if self.attempted == 0:
            return 0
        if self.failed == self.attempted:
            return 1
        if self.failed > self.attempted / 2:
            return 1
        if self.chunks_added == 0 and self.db_chunks == 0:
            logger.error("Ingest produced no chunks and collection has zero chunks in the database")
            return 1
        return 0

    def log_summary(self, collection: str) -> None:
        failed_list = ", ".join(self.failed_ids) if self.failed_ids else "none"
        logger.info(
            "INGEST SUMMARY collection=%s ok=%s unchanged=%s failed=%s "
            "chunks_added=%s embed_calls=%s throttle_retries=%s failed_ids=%s",
            collection,
            self.ok,
            self.unchanged,
            self.failed,
            self.chunks_added,
            self.embed_calls,
            self.throttle_retries,
            failed_list,
        )
        logger.info(
            "DB TOTALS collection=%s sources=%s documents=%s chunks=%s",
            collection,
            self.db_sources,
            self.db_documents,
            self.db_chunks,
        )


@dataclass(frozen=True)
class _SourceOutcome:
    status: str
    chunks: int = 0
    src_id: str | None = None
    error: str | None = None


def _try_ingest_source(
    conn: psycopg.Connection,
    src: SourceRecord,
    collection: str,
    cache: Path,
) -> _SourceOutcome | Literal["throttled"]:
    try:
        with conn.transaction():
            status, chunks = _ingest_one(conn, src, collection, cache)
        return _SourceOutcome(status, chunks=chunks)
    except EmbeddingThrottledError as exc:
        logger.warning("Throttled %s, deferring to retry pass: %s", src.id, exc)
        return "throttled"
    except Exception as exc:
        logger.error("FAILED %s %s: %s", src.id, src.url, exc)
        return _SourceOutcome("failed", src_id=src.id, error=str(exc))


def _apply_ingest_outcome(summary: IngestSummary, outcome: _SourceOutcome) -> None:
    if outcome.status == "unchanged":
        summary.unchanged += 1
    elif outcome.status == "ok":
        summary.ok += 1
        summary.chunks_added += outcome.chunks
    elif outcome.status == "failed":
        summary.failed += 1
        if outcome.src_id:
            summary.failed_ids.append(outcome.src_id)


def _load_normalised_markdown(src: SourceRecord, cache: Path) -> str:
    cache_file = cache / f"{src.id}.md"
    if cache_file.exists():
        raw = cache_file.read_text(encoding="utf-8")
    else:
        raw = fetch_source_markdown(src)
    markdown = normalise_text(raw)
    if markdown != raw or not cache_file.exists():
        cache_file.write_text(markdown, encoding="utf-8")
    return markdown


def ingest_collection(
    collection: str,
    *,
    sources_path: Path,
    limit: int | None = None,
) -> IngestSummary:
    run_migrations(db_dsn())
    sources = load_sources(str(sources_path))
    if limit is not None:
        sources = sources[:limit]
    cache = Path(CACHE_DIR)
    cache.mkdir(parents=True, exist_ok=True)
    summary = IngestSummary()
    throttle_queue: list[SourceRecord] = []
    with psycopg.connect(db_dsn()) as conn:
        register_vector(conn)
        for src in sources:
            outcome = _try_ingest_source(conn, src, collection, cache)
            if outcome == "throttled":
                throttle_queue.append(src)
            else:
                _apply_ingest_outcome(summary, outcome)

        if throttle_queue:
            pause = int(os.environ.get("EMBED_THROTTLE_RETRY_PAUSE_SEC", "30"))
            logger.info(
                "Throttle retry pass: sleeping %ss before retrying %s sources",
                pause,
                len(throttle_queue),
            )
            time.sleep(pause)
            for src in throttle_queue:
                outcome = _try_ingest_source(conn, src, collection, cache)
                if outcome == "throttled":
                    _apply_ingest_outcome(summary, _SourceOutcome("failed", src_id=src.id))
                else:
                    _apply_ingest_outcome(summary, outcome)

        summary.db_sources, summary.db_documents, summary.db_chunks = _collection_db_totals(
            conn, collection
        )
        conn.commit()
    embed_stats = get_embed_stats()
    summary.embed_calls = embed_stats["calls"]
    summary.throttle_retries = embed_stats["throttle_retries"]
    summary.log_summary(collection)
    return summary


def _collection_db_totals(conn: psycopg.Connection, collection: str) -> tuple[int, int, int]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM sources WHERE collection = %s",
            (collection,),
        )
        sources = cur.fetchone()[0]
        cur.execute(
            "SELECT count(*) FROM documents WHERE collection = %s",
            (collection,),
        )
        documents = cur.fetchone()[0]
        cur.execute(
            "SELECT count(*) FROM chunks WHERE collection = %s",
            (collection,),
        )
        chunks = cur.fetchone()[0]
    return sources, documents, chunks


def _source_is_fully_ingested(
    cur: psycopg.Cursor,
    source_id: str,
    collection: str,
    doc_hash: str,
    embedding_model: str,
) -> bool:
    cur.execute(
        """
        SELECT d.content_hash
        FROM documents d
        WHERE d.source_id = %s AND d.collection = %s
        ORDER BY d.document_id DESC
        LIMIT 1
        """,
        (source_id, collection),
    )
    row = cur.fetchone()
    if not row or row[0] != doc_hash:
        return False
    cur.execute(
        """
        SELECT 1
        FROM chunks c
        INNER JOIN documents d ON d.document_id = c.document_id
        WHERE c.source_id = %s
          AND d.content_hash = %s
          AND c.collection = %s
          AND c.embedding_model = %s
        LIMIT 1
        """,
        (source_id, doc_hash, collection, embedding_model),
    )
    return cur.fetchone() is not None


def _upsert_source(
    cur: psycopg.Cursor,
    src: SourceRecord,
    collection: str,
    doc_hash: str,
) -> None:
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
            collection = EXCLUDED.collection,
            title = EXCLUDED.title,
            authors = EXCLUDED.authors,
            year = EXCLUDED.year,
            source_url = EXCLUDED.source_url,
            licence = EXCLUDED.licence,
            licence_url = EXCLUDED.licence_url,
            licence_class = EXCLUDED.licence_class,
            nc_flag = EXCLUDED.nc_flag,
            nd_flag = EXCLUDED.nd_flag,
            attribution_text = EXCLUDED.attribution_text,
            format = EXCLUDED.format,
            content_hash = EXCLUDED.content_hash,
            updated_at = now()
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


def _ingest_one(
    conn: psycopg.Connection,
    src: SourceRecord,
    collection: str,
    cache: Path,
) -> tuple[str, int]:
    markdown = _load_normalised_markdown(src, cache)
    doc_hash = content_hash(markdown)
    chunks_added = 0
    with conn.cursor() as cur:
        if _source_is_fully_ingested(cur, src.id, collection, doc_hash, DEFAULT_MODEL):
            _upsert_source(cur, src, collection, doc_hash)
            logger.info("Unchanged %s, skipping chunks", src.id)
            return "unchanged", 0
        _upsert_source(cur, src, collection, doc_hash)
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
            return "ok", 0
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
                RETURNING chunk_id
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
            if cur.fetchone():
                chunks_added += 1
    return "ok", chunks_added

from __future__ import annotations

import logging
from dataclasses import dataclass, field
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


@dataclass
class IngestSummary:
    ok: int = 0
    unchanged: int = 0
    failed: int = 0
    chunks_added: int = 0
    failed_ids: list[str] = field(default_factory=list)

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
        return 0

    def log_summary(self, collection: str) -> None:
        failed_list = ", ".join(self.failed_ids) if self.failed_ids else "none"
        logger.info(
            "INGEST SUMMARY collection=%s ok=%s unchanged=%s failed=%s "
            "chunks_added=%s failed_ids=%s",
            collection,
            self.ok,
            self.unchanged,
            self.failed,
            self.chunks_added,
            failed_list,
        )


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
    with psycopg.connect(db_dsn()) as conn:
        register_vector(conn)
        for src in sources:
            try:
                with conn.transaction():
                    status, chunks = _ingest_one(conn, src, collection, cache)
                if status == "unchanged":
                    summary.unchanged += 1
                else:
                    summary.ok += 1
                summary.chunks_added += chunks
            except Exception as exc:
                logger.error("FAILED %s %s: %s", src.id, src.url, exc)
                summary.failed += 1
                summary.failed_ids.append(src.id)
        conn.commit()
    summary.log_summary(collection)
    return summary


def _ingest_one(
    conn: psycopg.Connection,
    src: SourceRecord,
    collection: str,
    cache: Path,
) -> tuple[str, int]:
    cache_file = cache / f"{src.id}.md"
    if cache_file.exists():
        markdown = cache_file.read_text(encoding="utf-8")
    else:
        markdown = fetch_source_markdown(src)
        cache_file.write_text(markdown, encoding="utf-8")
    doc_hash = content_hash(markdown)
    chunks_added = 0
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
            return "unchanged", 0
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

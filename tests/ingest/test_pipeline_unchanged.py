from __future__ import annotations

import os
from unittest.mock import patch

import psycopg
import pytest
from pgvector.psycopg import register_vector

from ingest.chunking import content_hash
from ingest.embed import DEFAULT_MODEL, to_vector
from ingest.licence import SourceRecord
from ingest.migrations.runner import run_migrations
from ingest.pipeline import IngestSummary, _ingest_one, ingest_collection


def _dsn() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://rag:raglocal@localhost:5432/ragplatform",
    )


@pytest.fixture()
def db_conn(tmp_path):
    dsn = _dsn()
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
    except psycopg.OperationalError:
        pytest.skip("Postgres not available")
    run_migrations(dsn)
    cache = tmp_path / "cache"
    cache.mkdir()
    with psycopg.connect(dsn) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chunks WHERE source_id = 'cs-regression'")
            cur.execute("DELETE FROM documents WHERE source_id = 'cs-regression'")
            cur.execute("DELETE FROM sources WHERE source_id = 'cs-regression'")
        conn.commit()
        yield conn, cache
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chunks WHERE source_id = 'cs-regression'")
            cur.execute("DELETE FROM documents WHERE source_id = 'cs-regression'")
            cur.execute("DELETE FROM sources WHERE source_id = 'cs-regression'")
        conn.commit()


def _fake_source() -> SourceRecord:
    return SourceRecord(
        id="cs-regression",
        title="Regression",
        authors=["Test"],
        year=None,
        url="https://example.com/cs-regression",
        licence="CC-BY-4.0",
        licence_url="https://creativecommons.org/licenses/by/4.0/",
        licence_class="A",
        nc_flag=False,
        nd_flag=False,
        attribution_text="Regression test source",
        format="fixture",
    )


def test_ingests_when_source_row_exists_without_chunks(db_conn):
    conn, cache = db_conn
    markdown = "## Section one\n\nBody text for regression ingest.\n"
    doc_hash = content_hash(markdown)
    src = _fake_source()
    cache_file = cache / f"{src.id}.md"
    cache_file.write_text(markdown, encoding="utf-8")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sources (
                source_id, collection, title, authors, source_url,
                licence, licence_url, licence_class, nc_flag, nd_flag,
                attribution_text, format, content_hash
            ) VALUES (
                %s, 'complex-systems', %s, ARRAY['Test'],
                %s, 'CC-BY-4.0', 'https://creativecommons.org/licenses/by/4.0/',
                'A', false, false, 'Regression test source', 'fixture', %s
            )
            """,
            (src.id, src.title, src.url, doc_hash),
        )
    conn.commit()

    fake_vec = [0.1] * 1024
    with patch("ingest.pipeline.embed_texts", return_value=[fake_vec]):
        status, chunks_added = _ingest_one(conn, src, "complex-systems", cache)
    conn.commit()

    assert status == "ok"
    assert chunks_added >= 1
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT count(*)
            FROM chunks
            WHERE source_id = %s AND embedding_model = %s
            """,
            (src.id, DEFAULT_MODEL),
        )
        assert cur.fetchone()[0] >= 1


def test_unchanged_when_document_and_chunks_exist(db_conn):
    conn, cache = db_conn
    markdown = "## Cached\n\nAlready ingested.\n"
    doc_hash = content_hash(markdown)
    src = _fake_source()
    cache_file = cache / f"{src.id}.md"
    cache_file.write_text(markdown, encoding="utf-8")
    vec = to_vector([0.2] * 1024)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sources (
                source_id, collection, title, authors, source_url,
                licence, licence_url, licence_class, nc_flag, nd_flag,
                attribution_text, format, content_hash
            ) VALUES (
                %s, 'complex-systems', %s, ARRAY['Test'],
                %s, 'CC-BY-4.0', 'https://creativecommons.org/licenses/by/4.0/',
                'A', false, false, 'Regression test source', 'fixture', %s
            )
            """,
            (src.id, src.title, src.url, doc_hash),
        )
        cur.execute(
            """
            INSERT INTO documents (source_id, collection, normalised_text, content_hash)
            VALUES (%s, 'complex-systems', %s, %s)
            RETURNING document_id
            """,
            (src.id, markdown, doc_hash),
        )
        document_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO chunks (
                source_id, document_id, collection, chunk_index, section_path,
                text, token_count, chunk_hash, embedding, embedding_model
            ) VALUES (
                %s, %s, 'complex-systems', 0, 's', 'Already ingested.', 3,
                'regression-chunk-hash', %s, %s
            )
            """,
            (src.id, document_id, vec, DEFAULT_MODEL),
        )
    conn.commit()

    with patch("ingest.pipeline.embed_texts") as embed_mock:
        status, chunks_added = _ingest_one(conn, src, "complex-systems", cache)

    assert status == "unchanged"
    assert chunks_added == 0
    embed_mock.assert_not_called()


def test_exit_code_fails_when_no_chunks_in_db():
    summary = IngestSummary(chunks_added=0, db_chunks=0, db_sources=1, db_documents=0)
    summary.ok = 1
    assert summary.exit_code() == 1


def test_ingest_collection_logs_db_totals(db_conn, tmp_path, caplog):
    import logging

    _conn, cache = db_conn
    caplog.set_level(logging.INFO)
    sources_yaml = tmp_path / "sources.yaml"
    sources_yaml.write_text(
        """
sources:
  - id: cs-regression
    title: Regression
    authors: [Test]
    year: null
    url: https://example.com/cs-regression
    licence: CC-BY-4.0
    licence_url: https://creativecommons.org/licenses/by/4.0/
    licence_class: A
    nc_flag: false
    nd_flag: false
    attribution_text: Regression test source
    format: fixture
""",
        encoding="utf-8",
    )
    (cache / "cs-regression.md").write_text("## Totals\n\nLogging check body.\n", encoding="utf-8")
    with (
        patch("ingest.pipeline.CACHE_DIR", str(cache)),
        patch("ingest.pipeline.embed_texts", return_value=[[0.3] * 1024, [0.4] * 1024]),
    ):
        summary = ingest_collection("complex-systems", sources_path=sources_yaml)
    assert summary.db_sources >= 1
    assert "DB TOTALS collection=complex-systems" in caplog.text

from __future__ import annotations

from dataclasses import dataclass

import psycopg
from pgvector.psycopg import register_vector

from app.core.rrf import reciprocal_rank_fusion
from ingest.embed import embed_texts


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    source_id: str
    text: str
    score: float
    rank: int
    licence_class: str
    attribution_text: str
    source_url: str
    title: str


class HybridRetriever:
    def __init__(self, dsn: str):
        self.dsn = dsn

    def retrieve(
        self,
        query: str,
        *,
        collection: str,
        top_lexical: int = 50,
        top_vector: int = 50,
        top_fused: int = 8,
    ) -> list[RetrievedChunk]:
        [query_vec] = embed_texts([query])
        with psycopg.connect(self.dsn) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.chunk_id
                    FROM chunks c
                    WHERE c.collection = %s
                    ORDER BY ts_rank(c.tsv, plainto_tsquery('english', %s)) DESC
                    LIMIT %s
                    """,
                    (collection, query, top_lexical),
                )
                lexical_ids = [r[0] for r in cur.fetchall()]
                cur.execute(
                    """
                    SELECT c.chunk_id
                    FROM chunks c
                    WHERE c.collection = %s
                    ORDER BY c.embedding <=> %s
                    LIMIT %s
                    """,
                    (collection, query_vec, top_vector),
                )
                vector_ids = [r[0] for r in cur.fetchall()]
            fused = reciprocal_rank_fusion([lexical_ids, vector_ids], top_n=top_fused)
            if not fused:
                return []
            ids = [f.item_id for f in fused]
            score_map = {f.item_id: f.score for f in fused}
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.chunk_id, c.source_id, c.text, s.licence_class,
                           s.attribution_text, s.source_url, s.title
                    FROM chunks c
                    JOIN sources s ON s.source_id = c.source_id
                    WHERE c.chunk_id = ANY(%s)
                    """,
                    (ids,),
                )
                rows = {r[0]: r for r in cur.fetchall()}
            out: list[RetrievedChunk] = []
            for rank, chunk_id in enumerate(ids, start=1):
                row = rows[chunk_id]
                out.append(
                    RetrievedChunk(
                        chunk_id=row[0],
                        source_id=row[1],
                        text=row[2],
                        score=score_map[chunk_id],
                        rank=rank,
                        licence_class=row[3],
                        attribution_text=row[4],
                        source_url=row[5],
                        title=row[6],
                    )
                )
            return out

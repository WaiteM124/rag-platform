from __future__ import annotations

import json
import logging
import mimetypes
import os
import time
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.api.citations import build_citations
from app.api.langfuse_trace import init_langfuse_at_startup, maybe_trace
from app.api.metrics import emit_daily_spend_gbp
from app.api.rate_limit import client_ip, rate_limited
from app.api.request_log import build_metrics_log_line, emit_request_metrics_log
from app.api.settings import get_settings, warn_langfuse_placeholder_once
from app.api.spend import record_spend_gbp, spend_cap_exceeded, spend_today_gbp
from app.api.stage_timer import StageTimer
from app.core.answer import SYSTEM_PROMPT, AnswerEngine
from app.core.bedrock import ANSWER_MODEL, converse_stream
from app.core.composer import LicenceComposer
from app.core.cost import (
    TokenUsage,
    combine_costs,
    estimate_embed_cost,
    load_price_cards,
)
from ingest.config import db_dsn
from ingest.migrations.runner import run_migrations

logger = logging.getLogger(__name__)

ALLOWED_COLLECTIONS = frozenset({"complex-systems"})

# Actual answer stages on /api/ask (no rerank step exists in this codebase).
STAGE_QUERY_EMBEDDING = "query_embedding"
STAGE_VECTOR_RETRIEVAL = "vector_retrieval"
STAGE_PROMPT_BUILD = "prompt_build"
STAGE_GENERATION = "generation"
STAGE_STREAM_TO_CLIENT = "stream_to_client"
STAGE_OUTPUT_GUARD = "output_guard"

app = FastAPI(title="RAG Platform", version="0.2.0")


class AskBody(BaseModel):
    collection: str
    question: str = Field(max_length=1000)


@app.on_event("startup")
def on_startup() -> None:
    try:
        run_migrations(db_dsn())
    except Exception:
        logger.exception("Migration startup failed")
    # Warn once if Terraform placeholders are still in Secrets Manager.
    warn_langfuse_placeholder_once(
        os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
        os.environ.get("LANGFUSE_SECRET_KEY", ""),
    )
    init_langfuse_at_startup()


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none';"
    )
    settings = get_settings()
    if settings.https_enabled or request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    try:
        with psycopg.connect(db_dsn(), connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return {"status": "ready"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc


@app.get("/api/collections")
def list_collections() -> JSONResponse:
    enabled = [{"id": "complex-systems", "label": "Complex Systems", "enabled": True}]
    coming = [{"id": "uk-tax", "label": "UK Tax", "enabled": False, "status": "coming_soon"}]
    try:
        with psycopg.connect(db_dsn()) as conn, conn.cursor() as cur:
            cur.execute("SELECT DISTINCT collection, COUNT(*) FROM sources GROUP BY collection")
            counts = {row[0]: row[1] for row in cur.fetchall()}
            for item in enabled:
                item["source_count"] = counts.get(item["id"], 0)
    except Exception:
        for item in enabled:
            item["source_count"] = None
    return JSONResponse({"collections": enabled + coming})


@app.post("/api/ask")
async def ask(body: AskBody, request: Request) -> StreamingResponse:
    settings = get_settings()
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question required")
    if len(question) > settings.question_max_chars:
        raise HTTPException(status_code=400, detail="question too long")
    if body.collection not in ALLOWED_COLLECTIONS:
        raise HTTPException(status_code=400, detail="collection not available")

    peer = request.client.host if request.client else None
    ip = client_ip(request.headers.get("x-forwarded-for"), peer)
    if rate_limited(ip):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    if spend_cap_exceeded(settings.daily_spend_cap_gbp):
        raise HTTPException(
            status_code=503,
            detail="daily spend cap reached; try again tomorrow UTC",
        )

    request_id = str(uuid.uuid4())
    engine = AnswerEngine(db_dsn())
    timer = StageTimer()
    model_id = settings.answer_model_id or ANSWER_MODEL
    price_cards = load_price_cards()

    async def event_stream() -> AsyncIterator[str]:
        answer_parts: list[str] = []
        usage = {"input_tokens": 0, "output_tokens": 0}
        chunks = []
        answer = ""
        embed_tokens = 0
        embed_model = ""
        embed_est = estimate_embed_cost(0, "", price_cards)

        with maybe_trace(
            "ask",
            {"collection": body.collection},
            request_id=request_id,
        ) as trace:
            try:
                # HybridRetriever times query_embedding vs vector_retrieval internally
                # (embed call + lexical/vector/RRF fetch). No rerank stage exists.
                with trace.span(
                    "retrieval",
                    metadata={"collection": body.collection},
                ) as retrieval_root:
                    chunks = engine.retriever.retrieve(question, collection=body.collection)
                    timing = engine.retriever._last_timing
                    timer.stages_ms[STAGE_QUERY_EMBEDDING] = timing.query_embedding_ms
                    timer.stages_ms[STAGE_VECTOR_RETRIEVAL] = timing.vector_retrieval_ms
                    embed_tokens = engine.retriever._last_embed_input_tokens
                    embed_model = engine.retriever._last_embed_model_id
                    embed_est = estimate_embed_cost(embed_tokens, embed_model, price_cards)
                    try:
                        retrieval_root.update(
                            output={
                                "n_chunks": len(chunks),
                                "stages_ms": {
                                    STAGE_QUERY_EMBEDDING: timing.query_embedding_ms,
                                    STAGE_VECTOR_RETRIEVAL: timing.vector_retrieval_ms,
                                },
                            }
                        )
                    except Exception:
                        pass

                with trace.generation(
                    name=STAGE_QUERY_EMBEDDING,
                    model=embed_model,
                    usage={
                        "input": embed_tokens,
                        "output": 0,
                        "total": embed_tokens,
                        "unit": "TOKENS",
                    },
                    metadata={
                        "stage": STAGE_QUERY_EMBEDDING,
                        "ms": timer.stages_ms.get(STAGE_QUERY_EMBEDDING),
                        "cost_status": embed_est.status,
                    },
                    cost_details=({"total": embed_est.usd} if embed_est.usd is not None else None),
                ):
                    pass

                with timer.stage(STAGE_PROMPT_BUILD):
                    with trace.span(STAGE_PROMPT_BUILD) as prompt_span:
                        context = engine.composer.context_blocks(chunks)
                        user_text = f"Question:\n{question}\n\nContext:\n{context}"
                        try:
                            prompt_span.update(
                                output={
                                    "context_blocks": len(chunks),
                                    "prompt_chars": len(user_text),
                                }
                            )
                        except Exception:
                            pass

                # Split Bedrock wait time (generation) from yielding SSE deltas
                # (stream_to_client) so client/network lag is not billed to either
                # generation or the licence guard.
                generation_ms = 0.0
                stream_ms = 0.0
                with trace.generation(
                    name=STAGE_GENERATION,
                    model=model_id,
                    metadata={"stage": STAGE_GENERATION},
                ) as gen_obs:
                    try:
                        t_bedrock = time.perf_counter()
                        stream, usage = converse_stream(
                            messages=[
                                {
                                    "role": "user",
                                    "content": [{"text": user_text}],
                                }
                            ],
                            system=SYSTEM_PROMPT,
                            model_id=model_id,
                        )
                        generation_ms += (time.perf_counter() - t_bedrock) * 1000.0
                        stream_iter = iter(stream)
                        while True:
                            t_wait = time.perf_counter()
                            try:
                                chunk = next(stream_iter)
                            except StopIteration:
                                generation_ms += (time.perf_counter() - t_wait) * 1000.0
                                break
                            generation_ms += (time.perf_counter() - t_wait) * 1000.0
                            answer_parts.append(chunk)
                            payload = {"type": "delta", "text": chunk}
                            t_yield = time.perf_counter()
                            yield f"data: {json.dumps(payload)}\n\n"
                            stream_ms += (time.perf_counter() - t_yield) * 1000.0
                    except Exception as exc:
                        logger.exception("ask stream failed")
                        err = {"type": "error", "message": str(exc)[:200]}
                        yield f"data: {json.dumps(err)}\n\n"
                        return

                    in_tok = int(usage.get("input_tokens", 0))
                    out_tok = int(usage.get("output_tokens", 0))
                    gen_est = TokenUsage(in_tok, out_tok, model_id).estimate_cost(price_cards)
                    try:
                        gen_obs.update(
                            usage={
                                "input": in_tok,
                                "output": out_tok,
                                "total": in_tok + out_tok,
                                "unit": "TOKENS",
                            },
                            cost_details=(
                                {"total": gen_est.usd} if gen_est.usd is not None else None
                            ),
                            metadata={
                                "cost_usd": gen_est.usd,
                                "cost_status": gen_est.status,
                            },
                            output={"answer_len": len("".join(answer_parts))},
                        )
                    except Exception:
                        pass

                timer.stages_ms[STAGE_GENERATION] = round(generation_ms, 3)
                timer.stages_ms[STAGE_STREAM_TO_CLIENT] = round(stream_ms, 3)

                answer = "".join(answer_parts)
                with timer.stage(STAGE_OUTPUT_GUARD):
                    with trace.span(STAGE_OUTPUT_GUARD) as guard_span:
                        composer = LicenceComposer()
                        answer, licence_ok = composer.apply_output_policy(answer, chunks)
                        try:
                            guard_span.update(output={"licence_compliant": licence_ok})
                        except Exception:
                            pass

            except Exception as exc:
                logger.exception("ask pipeline failed")
                err = {"type": "error", "message": str(exc)[:200]}
                yield f"data: {json.dumps(err)}\n\n"
                return

            in_tok = int(usage.get("input_tokens", 0))
            out_tok = int(usage.get("output_tokens", 0))
            gen_est = TokenUsage(in_tok, out_tok, model_id).estimate_cost(price_cards)
            total_est = combine_costs(embed_est, gen_est)
            cost_usd = total_est.usd
            cost_status = total_est.status
            cost_gbp = (cost_usd * settings.usd_to_gbp) if cost_usd is not None else None

            if cost_gbp is not None:
                try:
                    record_spend_gbp(cost_gbp)
                    with psycopg.connect(db_dsn()) as conn:
                        today_total = spend_today_gbp(conn)
                    emit_daily_spend_gbp(today_total)
                except Exception:
                    logger.exception("spend metric failed")

            total_ms = timer.total_ms()
            stages = timer.as_dict()
            tokens = {
                "embed_input": embed_tokens,
                "generation_input": in_tok,
                "generation_output": out_tok,
            }
            models = {
                "embedding": embed_model,
                "generation": model_id,
            }
            metrics = {
                "request_id": request_id,
                "stages_ms": stages,
                "total_ms": total_ms,
                "tokens": tokens,
                "models": models,
                "cost_usd": cost_usd,
                "cost_gbp": round(cost_gbp, 6) if cost_gbp is not None else None,
                "cost_status": cost_status,
            }

            try:
                emit_request_metrics_log(
                    build_metrics_log_line(
                        request_id=request_id,
                        collection=body.collection,
                        question=question,
                        answer_len=len(answer),
                        models=models,
                        stages_ms=stages,
                        total_ms=total_ms,
                        tokens=tokens,
                        cost_usd=cost_usd,
                        cost_status=cost_status,
                    )
                )
            except Exception:
                logger.exception("metrics log failed")

            try:
                trace.update(
                    output={
                        "answer_len": len(answer),
                        "cost_usd": cost_usd,
                        "cost_status": cost_status,
                        "total_ms": total_ms,
                    }
                )
            except Exception:
                pass

            final = {
                "type": "done",
                "answer": answer,
                "citations": build_citations(answer, chunks),
                "latency_ms": int(total_ms),
                "tokens": {
                    "input": in_tok,
                    "output": out_tok,
                    "embed_input": embed_tokens,
                    "model": model_id,
                },
                "cost_gbp": round(cost_gbp, 6) if cost_gbp is not None else None,
                "cost_usd": cost_usd,
                "cost_status": cost_status,
                "metrics": metrics,
            }
            yield f"data: {json.dumps(final)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def resolve_static_file(root: Path, full_path: str) -> Path | None:
    """Return a file under root for full_path, or None for SPA / missing / unsafe paths."""
    if not full_path or full_path.endswith("/"):
        return None
    resolved_root = root.resolve()
    candidate = (resolved_root / full_path).resolve()
    if not candidate.is_relative_to(resolved_root):
        return None
    if candidate.is_file():
        return candidate
    return None


static_root = Path(os.environ.get("STATIC_DIR", get_settings().static_dir))
if static_root.is_dir():
    assets_dir = static_root / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        file_path = resolve_static_file(static_root, full_path)
        if file_path is not None:
            media_type, _ = mimetypes.guess_type(str(file_path))
            return FileResponse(file_path, media_type=media_type)
        return FileResponse(static_root / "index.html")

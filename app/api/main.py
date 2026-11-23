from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import AsyncIterator
from pathlib import Path

import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.api.citations import build_citations
from app.api.langfuse_trace import maybe_trace
from app.api.metrics import emit_daily_spend_gbp
from app.api.rate_limit import client_ip, rate_limited
from app.api.settings import get_settings
from app.api.spend import record_spend_gbp, spend_cap_exceeded, spend_today_gbp
from app.core.answer import SYSTEM_PROMPT, AnswerEngine
from app.core.bedrock import ANSWER_MODEL, converse_stream
from app.core.composer import LicenceComposer
from app.core.cost import TokenUsage, load_price_cards
from ingest.config import db_dsn
from ingest.migrations.runner import run_migrations

logger = logging.getLogger(__name__)

ALLOWED_COLLECTIONS = frozenset({"complex-systems"})

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

    engine = AnswerEngine(db_dsn())
    t0 = time.perf_counter()

    trace = None
    with maybe_trace("ask", {"collection": body.collection}) as active_trace:
        trace = active_trace
        chunks = engine.retriever.retrieve(question, collection=body.collection)
        context = engine.composer.context_blocks(chunks)
        user_text = f"Question:\n{question}\n\nContext:\n{context}"

    async def event_stream() -> AsyncIterator[str]:
        answer_parts: list[str] = []
        usage = {"input_tokens": 0, "output_tokens": 0}
        try:
            stream, usage = converse_stream(
                messages=[{"role": "user", "content": [{"text": user_text}]}],
                system=SYSTEM_PROMPT,
                model_id=settings.answer_model_id or ANSWER_MODEL,
            )
            for chunk in stream:
                answer_parts.append(chunk)
                payload = {"type": "delta", "text": chunk}
                yield f"data: {json.dumps(payload)}\n\n"
        except Exception as exc:
            logger.exception("ask stream failed")
            err = {"type": "error", "message": str(exc)[:200]}
            yield f"data: {json.dumps(err)}\n\n"
            return

        answer = "".join(answer_parts)
        composer = LicenceComposer()
        answer, _ = composer.apply_output_policy(answer, chunks)
        in_tok = int(usage.get("input_tokens", 0))
        out_tok = int(usage.get("output_tokens", 0))
        model = settings.answer_model_id or ANSWER_MODEL
        cost_usd = TokenUsage(in_tok, out_tok, model).cost_usd(load_price_cards())
        cost_gbp = cost_usd * settings.usd_to_gbp
        record_spend_gbp(cost_gbp)
        try:
            with psycopg.connect(db_dsn()) as conn:
                today_total = spend_today_gbp(conn)
            emit_daily_spend_gbp(today_total)
        except Exception:
            logger.exception("spend metric failed")

        latency_ms = int((time.perf_counter() - t0) * 1000)
        if trace:
            try:
                trace.update(output={"answer_len": len(answer), "cost_gbp": cost_gbp})
            except Exception:
                pass
        final = {
            "type": "done",
            "answer": answer,
            "citations": build_citations(answer, chunks),
            "latency_ms": latency_ms,
            "tokens": {
                "input": in_tok,
                "output": out_tok,
                "model": settings.answer_model_id or ANSWER_MODEL,
            },
            "cost_gbp": round(cost_gbp, 6),
        }
        yield f"data: {json.dumps(final)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


static_root = Path(os.environ.get("STATIC_DIR", get_settings().static_dir))
if static_root.is_dir():
    app.mount("/assets", StaticFiles(directory=static_root / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        file_path = static_root / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_root / "index.html")

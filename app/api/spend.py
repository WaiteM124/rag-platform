from __future__ import annotations

import datetime as dt

import psycopg

from ingest.config import db_dsn


def _utc_today() -> dt.date:
    return dt.datetime.now(dt.UTC).date()


def spend_today_gbp(conn: psycopg.Connection) -> float:
    today = _utc_today()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COALESCE(total_gbp, 0) FROM daily_spend WHERE spend_date = %s",
            (today,),
        )
        row = cur.fetchone()
    return float(row[0]) if row else 0.0


def record_spend_gbp(amount_gbp: float) -> None:
    today = _utc_today()
    with psycopg.connect(db_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO daily_spend (spend_date, total_gbp)
                VALUES (%s, %s)
                ON CONFLICT (spend_date) DO UPDATE
                SET total_gbp = daily_spend.total_gbp + EXCLUDED.total_gbp,
                    updated_at = now()
                """,
                (today, amount_gbp),
            )
        conn.commit()


def spend_cap_exceeded(cap_gbp: float) -> bool:
    with psycopg.connect(db_dsn()) as conn:
        return spend_today_gbp(conn) >= cap_gbp

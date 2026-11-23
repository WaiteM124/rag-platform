CREATE TABLE IF NOT EXISTS daily_spend (
    spend_date DATE PRIMARY KEY,
    total_gbp NUMERIC(12, 6) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
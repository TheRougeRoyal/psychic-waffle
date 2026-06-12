CREATE TABLE IF NOT EXISTS saved_backtests (
    id               uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at       timestamptz   NOT NULL DEFAULT now(),
    ticker           text          NOT NULL,
    strategy         text          NOT NULL,
    start_date       text          NOT NULL,
    end_date         text,
    window           integer,
    std_multiplier   float,
    risk_free_rate   float,
    metrics          jsonb,
    total_return     float
);

CREATE INDEX IF NOT EXISTS idx_saved_backtests_ticker
    ON saved_backtests (ticker);

CREATE INDEX IF NOT EXISTS idx_saved_backtests_created_at
    ON saved_backtests (created_at DESC);


CREATE TABLE IF NOT EXISTS watchlist (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at  timestamptz NOT NULL DEFAULT now(),
    ticker      text        NOT NULL UNIQUE,

    name        text,
    exchange    text
);


CREATE TABLE IF NOT EXISTS alerts (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at    timestamptz NOT NULL DEFAULT now(),
    ticker        text        NOT NULL,
    strategy      text        NOT NULL,
    condition     text,
    threshold     float,
    triggered     boolean     NOT NULL DEFAULT false,
    triggered_at  timestamptz
);

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Client initialisation — deferred until first database access
# ---------------------------------------------------------------------------

def _load_env_file() -> None:
    env_path = Path(__file__).resolve().with_name(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key or key in os.environ:
            continue

        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()

        os.environ[key] = value


_load_env_file()

_client: Any | None = None


def get_client() -> Any:
    global _client
    if _client is None:
        supabase_module = importlib.import_module("supabase")

        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
        _client = supabase_module.create_client(url, key)
    return _client


# ---------------------------------------------------------------------------
# saved_backtests
# ---------------------------------------------------------------------------

def save_backtest(
    ticker: str,
    strategy: str,
    start_date: str,
    end_date: str | None,
    window: int | None,
    std_multiplier: float | None,
    risk_free_rate: float | None,
    metrics: dict,
) -> dict:
    """Insert a backtest result and return the inserted row."""
    total_return = metrics.get("total_return") if metrics else None

    row = {
        "ticker": ticker,
        "strategy": strategy,
        "start_date": start_date,
        "end_date": end_date,
        "window": window,
        "std_multiplier": std_multiplier,
        "risk_free_rate": risk_free_rate,
        "metrics": metrics,
        "total_return": total_return,
    }

    response = get_client().table("saved_backtests").insert(row).execute()
    return response.data[0]


def get_saved_backtests(limit: int = 20) -> list:
    """Return the *limit* most recent backtests ordered by created_at DESC."""
    response = (
        get_client().table("saved_backtests")
        .select("id, created_at, ticker, strategy, start_date, end_date, total_return, metrics")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


def delete_backtest(id: str) -> bool:
    """Delete a backtest by id. Returns True if a row was deleted."""
    response = (
        get_client().table("saved_backtests")
        .delete()
        .eq("id", id)
        .execute()
    )
    return len(response.data) > 0


# ---------------------------------------------------------------------------
# watchlist
# ---------------------------------------------------------------------------

def add_to_watchlist(
    ticker: str,
    name: str | None = None,
    exchange: str | None = None,
) -> dict:
    """Upsert a ticker into the watchlist. On conflict updates name/exchange."""
    row = {"ticker": ticker, "name": name, "exchange": exchange}

    response = (
        get_client().table("watchlist")
        .upsert(row, on_conflict="ticker")
        .execute()
    )
    return response.data[0]


def get_watchlist() -> list:
    """Return all watchlist rows ordered by created_at DESC."""
    response = (
        get_client().table("watchlist")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def remove_from_watchlist(ticker: str) -> bool:
    """Delete a ticker from the watchlist. Returns True if a row was deleted."""
    response = (
        get_client().table("watchlist")
        .delete()
        .eq("ticker", ticker)
        .execute()
    )
    return len(response.data) > 0

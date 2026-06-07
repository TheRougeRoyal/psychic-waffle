import os
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Client initialisation — happens once at import time
# ---------------------------------------------------------------------------

_url: str = os.environ.get("SUPABASE_URL", "")
_key: str = os.environ.get("SUPABASE_KEY", "")

if not _url:
    raise RuntimeError(
        "Missing environment variable: SUPABASE_URL. "
        "Set it to your Supabase project URL (https://<project>.supabase.co)."
    )
if not _key:
    raise RuntimeError(
        "Missing environment variable: SUPABASE_KEY. "
        "Set it to your Supabase anon/service-role key."
    )

supabase: Client = create_client(_url, _key)


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

    response = supabase.table("saved_backtests").insert(row).execute()
    return response.data[0]


def get_saved_backtests(limit: int = 20) -> list:
    """Return the *limit* most recent backtests ordered by created_at DESC."""
    response = (
        supabase.table("saved_backtests")
        .select("id, created_at, ticker, strategy, start_date, end_date, total_return, metrics")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


def delete_backtest(id: str) -> bool:
    """Delete a backtest by id. Returns True if a row was deleted."""
    response = (
        supabase.table("saved_backtests")
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
        supabase.table("watchlist")
        .upsert(row, on_conflict="ticker")
        .execute()
    )
    return response.data[0]


def get_watchlist() -> list:
    """Return all watchlist rows ordered by created_at DESC."""
    response = (
        supabase.table("watchlist")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def remove_from_watchlist(ticker: str) -> bool:
    """Delete a ticker from the watchlist. Returns True if a row was deleted."""
    response = (
        supabase.table("watchlist")
        .delete()
        .eq("ticker", ticker)
        .execute()
    )
    return len(response.data) > 0

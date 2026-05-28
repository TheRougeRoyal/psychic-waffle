import yfinance as yf
import asyncio
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime

async def sync(
    ticker: str,
    interval: str,
    since: datetime,
    till: Optional[datetime] = None
) -> List[Dict]:
    """
    Fetches historical OHLCV data using the yfinance library.

    Args:
        ticker: Ticker symbol (e.g., "AAPL").
        interval: Data interval (e.g., "1d", "1h").
        since: Start date as a datetime object.
        till: End date as a datetime object (defaults to now).

    Returns:
        A list of dictionaries with keys: date, open, high, low, close, volume.
    """
    loop = asyncio.get_event_loop()

    try:
        def fetch():
            # Use yf.download with auto_adjust=True to get adjusted close as 'Close'
            df = yf.download(
                tickers=ticker,
                start=since.strftime('%Y-%m-%d'),
                end=till.strftime('%Y-%m-%d') if till else None,
                interval=interval,
                progress=False,
                auto_adjust=True
            )
            return df

        df = await loop.run_in_executor(None, fetch)

        if df is None or df.empty:
            raise ValueError(f"No data found for ticker '{ticker}'. It may be delisted or the ticker is invalid.")

        # yfinance sometimes returns multi-index columns if only one ticker is passed
        # we flatten them if necessary
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        records = []
        for date, row in df.iterrows():
            # Use .item() or float() on the series if it's a single value
            # but since we flattened the columns, row["Open"] should be a scalar
            records.append({
                "date": date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]),
            })

        return records

    except Exception as e:
        raise Exception(f"Error fetching data for {ticker}: {str(e)}")

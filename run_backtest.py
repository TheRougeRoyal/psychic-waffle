import asyncio
import datetime
from data_fetcher import sync
from bollinger_strategy import apply_bollinger_strategy

async def run_backtest(ticker: str, start_date: datetime.datetime):
    print(f"Fetching data for {ticker}...")
    try:
        raw_data = await sync(ticker, "1d", start_date)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    # Extract only the close prices
    # raw_data is now a List of Dicts: [{"date": ..., "close": ..., ...}, ...]
    close_prices = [d["close"] for d in raw_data]

    print(f"Running Python backtest for {ticker}...")
    results = apply_bollinger_strategy(close_prices, window=20, k=2.0)

    total_return = sum(s["strategy_return"] for s in results)

    print("\n--- Backtest Results (Pure Python/NumPy) ---")
    print(f"Ticker: {ticker}")
    print(f"Total Strategy Return: {total_return * 100:.4f}%")
    print(f"Final Signal Position: {results[-1]['position']}")

if __name__ == "__main__":
    ticker_to_test = "SPY"
    start_dt = datetime.datetime.fromtimestamp(1664638429)

    asyncio.run(run_backtest(ticker_to_test, start_dt))

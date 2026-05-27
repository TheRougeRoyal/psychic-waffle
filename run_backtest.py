import asyncio
import datetime
import ctypes
from data_fetcher import sync

# C++ Structures
class Signal(ctypes.Structure):
    _fields_ = [
        ("price", ctypes.c_double),
        ("ma", ctypes.c_double),
        ("upper_band", ctypes.c_double),
        ("lower_band", ctypes.c_double),
        ("position", ctypes.c_int),
        ("daily_return", ctypes.c_double),
        ("strategy_return", ctypes.c_double),
    ]

# Load the C++ Shared Library
try:
    lib = ctypes.CDLL("./libbb_strategy.so")
except OSError:
    print("C++ library not found. Please run 'make' first.")
    exit(1)

# Define function signatures
lib.create_strategy.restype = ctypes.c_void_p
lib.create_strategy.argtypes = [ctypes.c_int, ctypes.c_double]

lib.destroy_strategy.argtypes = [ctypes.c_void_p]

lib.run_strategy.restype = ctypes.c_int
lib.run_strategy.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_double),
    ctypes.c_int,
    ctypes.POINTER(Signal)
]

async def run_backtest(ticker: str, start_date: datetime.datetime):
    print(f"Fetching data for {ticker}...")
    try:
        raw_data = await sync(ticker, "1d", start_date)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    # Extracts close prices as doubles
    close_prices = [d[3] for d in raw_data]
    n = len(close_prices)

    # Prepare C-compatible array
    prices_array = (ctypes.c_double * n)(*close_prices)
    results_array = (Signal * n)()

    # C++ strategy execution
    strat_ptr = lib.create_strategy(20, 2.0)
    try:
        num_results = lib.run_strategy(strat_ptr, prices_array, n, results_array)

        total_return = sum(res.strategy_return for res in results_array[:num_results])

        print("\n--- Backtest Results (via ctypes bridge) ---")
        print(f"Ticker: {ticker}")
        print(f"Total Strategy Return: {total_return * 100:.4f}%")
        print(f"Final Signal Position: {results_array[num_results-1].position}")
    finally:
        lib.destroy_strategy(strat_ptr)

if __name__ == "__main__":
    ticker_to_test = "SPY"
    start_dt = datetime.datetime.fromtimestamp(1664638429)

    asyncio.run(run_backtest(ticker_to_test, start_dt))

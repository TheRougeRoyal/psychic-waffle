"""
Bridge module connecting NSE real-time data API to C++ Bollinger Strategy.

This module demonstrates how to:
1. Fetch real-time stock data from NSE using nsetools
2. Connect the data to the C++ BollingerStrategy via C-API (ctypes)
3. Generate trading signals in real-time

Note: NSE access may be restricted in some environments. The module includes
fallback mechanisms and error handling.
"""

import time
import datetime
from typing import Optional, List, Dict
import ctypes

# Try to import nsetools, handle gracefully if not available or blocked
try:
    from nsetools import Nse
    NSETOOLS_AVAILABLE = True
except ImportError:
    NSETOOLS_AVAILABLE = False
    print("Warning: nsetools not available. Install with: pip install nsetools")

# Load the C++ strategy library
try:
    lib = ctypes.CDLL('./libbb_strategy.so')
    CPP_STRATEGY_AVAILABLE = True
except OSError as e:
    CPP_STRATEGY_AVAILABLE = False
    print(f"Warning: Could not load C++ strategy library: {e}")

# Define the Signal structure to match C++ struct
class Signal(ctypes.Structure):
    _fields_ = [
        ('date', ctypes.c_char_p),
        ('price', ctypes.c_double),
        ('ma', ctypes.c_double),
        ('upper_band', ctypes.c_double),
        ('lower_band', ctypes.c_double),
        ('position', ctypes.c_int),
        ('daily_return', ctypes.c_double),
        ('strategy_return', ctypes.c_double)
    ]

# Set up function pointers if library loaded
if CPP_STRATEGY_AVAILABLE:
    create_strategy = lib.create_strategy
    create_strategy.restype = ctypes.c_void_p
    create_strategy.argtypes = [ctypes.c_int, ctypes.c_double]

    destroy_strategy = lib.destroy_strategy
    destroy_strategy.restype = None
    destroy_strategy.argtypes = [ctypes.c_void_p]

    run_strategy = lib.run_strategy
    run_strategy.restype = ctypes.c_int
    run_strategy.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_double), ctypes.c_int, ctypes.POINTER(Signal)]
    # Note: The 'update' method from the C++ class is not exposed in the C-API extern "C" block
    # We use run_strategy with the full price history for each update


class NseDataBridge:
    """Bridge to fetch NSE data and feed it to C++ Bollinger Strategy."""

    def __init__(self, symbol: str = "RELIANCE", window: int = 20, std_dev: float = 2.0):
        """
        Initialize the bridge.

        Args:
            symbol: NSE stock symbol (e.g., "RELIANCE", "INFY")
            window: Bollinger Band window size
            std_dev: Standard deviation multiplier
        """
        self.symbol = symbol.upper()
        self.window = window
        self.std_dev = std_dev
        self.nse = None
        self.cpp_strategy_ptr = None
        self.price_history: List[float] = []

        # Initialize NSE connection if available
        if NSETOOLS_AVAILABLE:
            try:
                self.nse = Nse()
                # Test connection by getting index data (lighter than stock quote)
                _ = self.nse.get_index_list()
                print(f"NSE connection initialized for {self.symbol}")
            except Exception as e:
                print(f"Warning: Could not initialize NSE connection: {e}")
                self.nse = None

        # Initialize C++ strategy if available
        if CPP_STRATEGY_AVAILABLE:
            try:
                self.cpp_strategy_ptr = create_strategy(window, std_dev)
                print(f"C++ strategy initialized (window={window}, std_dev={std_dev})")
            except Exception as e:
                print(f"Warning: Could not initialize C++ strategy: {e}")
                self.cpp_strategy_ptr = None

    def get_live_quote(self) -> Optional[Dict]:
        """
        Fetch live quote for the symbol from NSE.

        Returns:
            Dictionary with quote data or None if failed
        """
        if not self.nse:
            print("Error: NSE not available")
            return None

        try:
            quote = self.nse.get_quote(self.symbol)
            if quote and 'priceInfo' in quote:
                price_info = quote['priceInfo']
                return {
                    'symbol': self.symbol,
                    'price': float(price_info.get('lastPrice', 0)),
                    'change': float(price_info.get('change', 0)),
                    'pChange': float(price_info.get('pChange', 0)),
                    'open': float(price_info.get('open', 0)),
                    'high': float(price_info.get('high', 0)),
                    'low': float(price_info.get('low', 0)),
                    'previousClose': float(price_info.get('previousClose', 0)),
                    'timestamp': datetime.datetime.now().isoformat()
                }
            else:
                print(f"Warning: Unexpected quote format for {self.symbol}")
                return None
        except Exception as e:
            print(f"Error fetching quote for {self.symbol}: {e}")
            return None

    def update_strategy_with_price(self, price: float) -> Optional[Signal]:
        """
        Update the C++ strategy with a new price and get the signal.

        For real-time updates, we need to maintain a rolling window of prices
        and periodically run the full backtest, or use the update method if
        available in C-API.

        Args:
            price: New price value

        Returns:
            Signal object or None if failed
        """
        if not self.cpp_strategy_ptr:
            print("Error: C++ strategy not available")
            return None

        # Add price to history
        self.price_history.append(price)

        # Keep only the last 'window' prices for efficiency
        if len(self.price_history) > self.window * 2:  # Keep some extra for safety
            self.price_history = self.price_history[-self.window * 2:]

        # If we have enough data, run the strategy on the full history
        if len(self.price_history) >= self.window:
            try:
                # Prepare data for C++ function
                n = len(self.price_history)
                prices_array = (ctypes.c_double * n)(*self.price_history)
                results = (Signal * n)()

                # Run strategy
                count = run_strategy(self.cpp_strategy_ptr, prices_array, n, results)

                if count > 0:
                    # Return the most recent signal
                    return results[count - 1]
                else:
                    print("Warning: No results returned from strategy")
                    return None

            except Exception as e:
                print(f"Error updating strategy: {e}")
                return None
        else:
            # Not enough data yet - return empty signal
            return Signal(
                date=b"",
                price=price,
                ma=0.0,
                upper_band=0.0,
                lower_band=0.0,
                position=0,
                daily_return=0.0,
                strategy_return=0.0
            )

    def get_live_signal(self) -> Optional[Dict]:
        """
        Get a live trading signal by fetching quote and updating strategy.

        Returns:
            Dictionary with signal data or None if failed
        """
        # Get live price
        quote = self.get_live_quote()
        if not quote:
            return None

        price = quote['price']

        # Update strategy and get signal
        signal = self.update_strategy_with_price(price)
        if not signal:
            return None

        # Convert Signal to dictionary
        return {
            'symbol': self.symbol,
            'price': quote['price'],
            'timestamp': quote['timestamp'],
            'ma': signal.ma,
            'upper_band': signal.upper_band,
            'lower_band': signal.lower_band,
            'position': signal.position,  # 1 = long, -1 = short, 0 = neutral
            'daily_return': signal.daily_return,
            'strategy_return': signal.strategy_return,
            'signal': 'LONG' if signal.position == 1 else 'SHORT' if signal.position == -1 else 'NEUTRAL'
        }

    def run_continuous(self, interval_seconds: int = 5):
        """
        Run continuous live signal generation.

        Args:
            interval_seconds: Time between updates in seconds
        """
        print(f"Starting continuous signal generation for {self.symbol}")
        print(f"Update interval: {interval_seconds} seconds")
        print("Press Ctrl+C to stop\n")

        try:
            while True:
                signal = self.get_live_signal()
                if signal:
                    print(f"[{signal['timestamp']}] {signal['symbol']}: "
                          f"Price=₹{signal['price']:.2f}, "
                          f"Signal={signal['signal']}, "
                          f"Position={signal['position']}, "
                          f"MA=₹{signal['ma']:.2f}, "
                          f"Bands=[{signal['lower_band']:.2f}, {signal['upper_band']:.2f}], "
                          f"Daily Return={signal['daily_return']:.4f}")
                else:
                    print(f"[{datetime.datetime.now().isoformat()}] Failed to get signal for {self.symbol}")

                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\nStopping live signal generation...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        if self.cpp_strategy_ptr and CPP_STRATEGY_AVAILABLE:
            destroy_strategy(self.cpp_strategy_ptr)
            self.cpp_strategy_ptr = None
            print("C++ strategy cleaned up")


def demo_backtest_mode():
    """
    Demonstrate the bridge in backtest mode using historical data.
    Since NSE historical data is not available via nsetools, we'll use yfinance
    or mock data for demonstration.
    """
    print("=== NSE-C++ Bridge Demo (Backtest Mode) ===")

    # Try to use yfinance for historical data if available
    try:
        import yfinance as yf
        import pandas as pd

        print("Fetching historical data using yfinance...")
        # Get data for RELIANCE.NS (NSE format for yfinance)
        ticker = yf.Ticker("RELIANCE.NS")
        hist = ticker.history(period="1mo", interval="1d")  # Last 1 month daily data

        if not hist.empty:
            prices = hist['Close'].tolist()
            dates = [d.strftime('%Y-%m-%d') for d in hist.index]

            print(f"Fetched {len(prices)} days of historical data for RELIANCE.NS")

            # Initialize bridge
            bridge = NseDataBridge(symbol="RELIANCE", window=20, std_dev=2.0)

            # Process historical data
            signals = []
            for i, (date, price) in enumerate(zip(dates, prices)):
                # Update price history
                bridge.price_history.append(price)

                # Once we have enough data, get signal
                if len(bridge.price_history) >= bridge.window:
                    signal = bridge.update_strategy_with_price(price)
                    if signal:
                        signals.append({
                            'date': date,
                            'price': price,
                            'signal': 'LONG' if signal.position == 1 else 'SHORT' if signal.position == -1 else 'NEUTRAL',
                            'position': signal.position,
                            'ma': signal.ma,
                            'upper': signal.upper_band,
                            'lower': signal.lower_band
                        })

            # Show recent signals
            print("\nRecent Signals:")
            for s in signals[-10:]:  # Last 10 signals
                print(f"  {s['date']}: Price=₹{s['price']:.2f}, {s['signal']}, "
                      f"MA=₹{s['ma']:.2f}, Bands=[{s['lower']:.2f}, {s['upper']:.2f}]")

            bridge.cleanup()
            return

    except ImportError:
        print("yfinance not available, using mock data...")

    # Fallback to mock data
    print("Using mock data for demonstration...")
    import random

    # Generate mock price data (random walk)
    base_price = 2500.0
    prices = []
    for i in range(50):
        change = random.uniform(-20, 20)
        base_price = max(base_price + change, 100)  # Keep price positive
        prices.append(base_price)

    print(f"Generated {len(prices)} mock prices")

    # Initialize bridge
    bridge = NseDataBridge(symbol="RELIANCE", window=20, std_dev=2.0)

    # Process mock data
    signals = []
    for i, price in enumerate(prices):
        bridge.price_history.append(price)

        if len(bridge.price_history) >= bridge.window:
            signal = bridge.update_strategy_with_price(price)
            if signal:
                signals.append({
                    'index': i,
                    'price': price,
                    'signal': 'LONG' if signal.position == 1 else 'SHORT' if signal.position == -1 else 'NEUTRAL',
                    'position': signal.position,
                    'ma': signal.ma,
                    'upper': signal.upper_band,
                    'lower': signal.lower_band
                })

    # Show recent signals
    print("\nRecent Signals (Mock Data):")
    for s in signals[-10:]:
        print(f"  Index {s['index']}: Price=₹{s['price']:.2f}, {s['signal']}, "
              f"MA=₹{s['ma']:.2f}, Bands=[{s['lower']:.2f}, {s['upper']:.2f}]")

    bridge.cleanup()


if __name__ == "__main__":
    print("NSE-C++ Bollinger Strategy Bridge")
    print("=" * 40)

    # Show what's available
    print(f"NSETools available: {NSETOOLS_AVAILABLE}")
    print(f"C++ Strategy available: {CPP_STRATEGY_AVAILABLE}")
    print()

    # Run demo
    demo_backtest_mode()

    print("\n" + "=" * 40)
    print("Demo completed.")
    print("To run live signals, uncomment the continuous run line below and ensure:")
    print("1. NSE access is allowed from this network")
    print("2. You have an active internet connection")
    print("# bridge = NseDataBridge('RELIANCE')")
    print("# bridge.run_continuous(interval_seconds=30)")
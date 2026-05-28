import numpy as np
from typing import List, Dict

def apply_sma_cross_strategy(prices: List[float], fast_window: int = 10, slow_window: int = 50) -> List[Dict]:
    """
    Implementation of the SMA Crossover strategy.
    Long when fast SMA crosses above slow SMA, short when fast crosses below.
    """
    p = np.array(prices)
    n = len(p)

    if n < slow_window:
        return []

    # 1. Calculate SMAs using sliding windows
    fast_windows = np.lib.stride_tricks.sliding_window_view(p, fast_window)
    slow_windows = np.lib.stride_tricks.sliding_window_view(p, slow_window)

    fast_ma_values = np.mean(fast_windows, axis=1)
    slow_ma_values = np.mean(slow_windows, axis=1)

    # Align fast_ma to slow_ma (fast_ma has more elements)
    # fast_ma starts at index fast_window-1, slow_ma starts at slow_window-1
    fast_ma_aligned = fast_ma_values[slow_window - fast_window:]

    # 2. Calculate Daily Log Returns
    daily_returns = np.diff(np.log(p))
    daily_returns = np.insert(daily_returns, 0, 0.0)

    results = []
    current_pos = 0

    for i in range(n):
        price = float(p[i])
        d_ret = float(daily_returns[i])

        if i < slow_window - 1:
            ma, upper, lower = 0.0, 0.0, 0.0
            s_ret = 0.0
            pos = 0
        else:
            idx = i - (slow_window - 1)
            ma = float(fast_ma_aligned[idx])
            upper = float(slow_ma_values[idx])
            lower = 0.0

            # 1. Calculate return based on position held from yesterday
            s_ret = current_pos * d_ret

            # 2. Update position for tomorrow based on crossover
            if i > slow_window - 1:
                prev_fast = fast_ma_aligned[idx - 1]
                prev_slow = slow_ma_values[idx - 1]

                # Long when fast crosses above slow
                if ma > upper and prev_fast <= prev_slow:
                    current_pos = 1
                # Short when fast crosses below slow
                elif ma < upper and prev_fast >= prev_slow:
                    current_pos = -1
            else: # First valid bar
                if ma > upper:
                    current_pos = 1
                elif ma < upper:
                    current_pos = -1

            pos = current_pos

        results.append({
            "price": price,
            "ma": ma,
            "upper_band": upper,
            "lower_band": lower,
            "position": pos,
            "daily_return": d_ret,
            "strategy_return": s_ret
        })

    return results

def apply_rsi_strategy(prices: List[float], period: int = 14) -> List[Dict]:

    """
    Implementation of the RSI strategy with Wilder's smoothing.

    Args:
        prices: List of closing prices.
        period: RSI period (default 14).

    Returns:
        A list of dictionaries containing the strategy metrics for each day.
    """
    p = np.array(prices)
    n = len(p)

    if n < period:
        return []

    # 1. Calculate RSI using Wilder's Smoothing
    diff = np.diff(p)
    gain = np.where(diff > 0, diff, 0.0)
    loss = np.where(diff < 0, -diff, 0.0)

    avg_gain = np.zeros(n)
    avg_loss = np.zeros(n)

    # Initial SMA for the first period
    avg_gain[period] = np.mean(gain[:period])
    avg_loss[period] = np.mean(loss[:period])

    for i in range(period + 1, n):
        # Wilder's smoothing: (PrevAvg * (n-1) + Current) / n
        avg_gain[i] = (avg_gain[i-1] * (period - 1) + gain[i-1]) / period
        avg_loss[i] = (avg_loss[i-1] * (period - 1) + loss[i-1]) / period

    rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss != 0)
    rsi_values = 100 - (100 / (1 + rs))

    # 2. Calculate Daily Log Returns
    daily_returns = np.diff(np.log(p))
    daily_returns = np.insert(daily_returns, 0, 0.0)

    # 3. Signal Generation and Position Management
    results = []
    current_pos = 0

    for i in range(n):
        price = float(p[i])
        d_ret = float(daily_returns[i])

        if i < period:
            rsi = 0.0
            s_ret = 0.0
            pos = 0
        else:
            rsi = float(rsi_values[i])

            # 1. Calculate return based on position held from yesterday
            s_ret = current_pos * d_ret

            # 2. Update position for tomorrow based on today's signal
            # Long entry: RSI crosses below 30
            if i > period and rsi < 30 and rsi_values[i-1] >= 30:
                current_pos = 1
            # Short entry: RSI crosses above 70
            elif i > period and rsi > 70 and rsi_values[i-1] <= 70:
                current_pos = -1
            # Exit toward 50
            elif current_pos == 1 and rsi >= 50:
                current_pos = 0
            elif current_pos == -1 and rsi <= 50:
                current_pos = 0

            pos = current_pos

        results.append({
            "price": price,
            "ma": rsi,
            "upper_band": 70.0,
            "lower_band": 30.0,
            "position": pos,
            "daily_return": d_ret,
            "strategy_return": s_ret
        })

    return results

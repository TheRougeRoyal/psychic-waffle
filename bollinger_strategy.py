import numpy as np
from typing import List, Dict

def apply_bollinger_strategy(prices: List[float], window: int = 20, k: float = 2.0) -> List[Dict]:
    """
    Pure Python/NumPy implementation of the Bollinger Band strategy.

    Args:
        prices: List of closing prices.
        window: Rolling window size for SMA and Std Dev.
        k: Standard deviation multiplier.

    Returns:
        A list of dictionaries containing the strategy metrics for each day.
    """
    p = np.array(prices)
    n = len(p)

    if n < window:
        return []

    # 1. Calculate Rolling SMA and Std Dev using NumPy sliding windows
    # sliding_window_view creates a view of the array with the window size
    windows = np.lib.stride_tricks.sliding_window_view(p, window)

    ma_values = np.mean(windows, axis=1)
    std_values = np.std(windows, axis=1)

    upper_values = ma_values + (k * std_values)
    lower_values = ma_values - (k * std_values)

    # 2. Calculate Daily Log Returns
    # log(p_t / p_{t-1})
    daily_returns = np.diff(np.log(p))
    # Prepend 0 to match original array length
    daily_returns = np.insert(daily_returns, 0, 0.0)

    # 3. Signal Generation and Position Management
    # The strategy starts producing signals only after the first 'window' days
    results = []
    current_position = 0

    # Fill the initial period where MA is not yet available
    for i in range(window - 1):
        results.append({
            "price": float(p[i]),
            "ma": 0.0,
            "upper_band": 0.0,
            "lower_band": 0.0,
            "position": 0,
            "daily_return": float(daily_returns[i]),
            "strategy_return": 0.0
        })

    # Process the rest of the data
    # Note: ma_values[0] corresponds to price p[window-1]
    for i in range(window - 1, n):
        idx = i - (window - 1)

        price = p[i]
        ma = ma_values[idx]
        upper = upper_values[idx]
        lower = lower_values[idx]

        # Cross Logic:
        # We need previous values to detect a "cross"
        if i > window - 1:
            prev_price = p[i-1]
            prev_ma = ma_values[idx-1]
            prev_std = std_values[idx-1]
            prev_lower = prev_ma - (k * prev_std)
            prev_upper = prev_ma + (k * prev_std)

            # Long: Price crosses below lower band from top
            if price < lower and prev_price >= prev_lower:
                current_position = 1
            # Short: Price crosses above upper band from below
            elif price > upper and prev_price <= prev_upper:
                current_position = -1

        # Strategy Return Calculation:
        # Position from the end of yesterday * today's return
        strat_return = 0.0
        if i > 0:
            # This mimics the C++ shift(1) logic: result[i].strat_return = result[i-1].position * return[i]
            # We need to look at what the position was BEFORE this signal was processed for today's return,
            # OR use a variable to track the "effective position".
            pass # Handled below by using the position from the previous iteration

        # We calculate strategy return using the position active AT THE START of the day
        # So we store the current_position, but the return uses the *previous* current_position.
        # Let's use a temporary variable to store the position for the NEXT day.

        # Wait, let's refine the loop to strictly follow the C++ a-posteriori logic:
        # results[i].strategy_return = results[i-1].position * results[i].daily_return;

    # Re-doing the loop for clarity and correctness relative to the C++ implementation
    results = []
    current_pos = 0

    for i in range(n):
        # Basic values
        price = float(p[i])
        d_ret = float(daily_returns[i])

        if i < window - 1:
            ma, upper, lower = 0.0, 0.0, 0.0
            # No signals in the warmup period
            s_ret = 0.0
            pos = 0
        else:
            idx = i - (window - 1)
            ma = float(ma_values[idx])
            upper = float(upper_values[idx])
            lower = float(lower_values[idx])

            # 1. Calculate return based on position held from yesterday
            s_ret = current_pos * d_ret

            # 2. Update position for tomorrow based on today's cross
            if i > window - 1:
                prev_price = p[i-1]
                prev_ma = ma_values[idx-1]
                prev_std = std_values[idx-1]
                prev_lower = prev_ma - (k * prev_std)
                prev_upper = prev_ma + (k * prev_std)

                if price < lower and prev_price >= prev_lower:
                    current_pos = 1
                elif price > upper and prev_price <= prev_upper:
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

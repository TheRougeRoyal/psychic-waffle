import numpy as np
from typing import List, Dict

def calculate_metrics(strategy_returns: List[float], close_prices: List[float], positions: List[int]) -> Dict[str, float]:
    """
    Calculates performance metrics for a trading strategy.

    Args:
        strategy_returns: List of daily log returns for the strategy.
        close_prices: List of closing prices for the asset.
        positions: List of positions (1 for long, -1 for short, 0 for flat).

    Returns:
        A dictionary containing key performance metrics.
    """
    # Convert to numpy arrays for vectorization
    strat_ret = np.array(strategy_returns)
    prices = np.array(close_prices)
    pos = np.array(positions)

    if len(strat_ret) == 0:
        return {}

    # 1. Buy and Hold Return
    # Since close_prices are absolute, compute log returns first
    bnh_log_returns = np.diff(np.log(prices))
    # To align with strategy_returns length (which has a 0 at start), prepend 0
    bnh_log_returns = np.insert(bnh_log_returns, 0, 0.0)
    total_bnh_log_ret = np.sum(bnh_log_returns)
    buy_and_hold_return = np.exp(total_bnh_log_ret) - 1

    # 2. Total Strategy Return
    total_strat_log_ret = np.sum(strat_ret)
    total_return = np.exp(total_strat_log_ret) - 1

    # 3. Annualized Return
    # (Mean daily log return * 252) converted back to arithmetic
    annualised_return = np.exp(np.mean(strat_ret) * 252) - 1

    # 4. Sharpe Ratio
    # (Mean / Std) * sqrt(252). Assumes risk-free rate is 0.
    std = np.std(strat_ret)
    sharpe_ratio = (np.mean(strat_ret) / std * np.sqrt(252)) if std != 0 else 0.0

    # 5. Max Drawdown
    # Cumulative returns curve
    cum_returns = np.exp(np.cumsum(strat_ret))
    # running maximum
    running_max = np.maximum.accumulate(cum_returns)
    drawdowns = (cum_returns / running_max) - 1
    max_drawdown = np.min(drawdowns)

    # 6. Win Rate
    # Percentage of days with positive strategy returns
    win_rate = np.mean(strat_ret > 0) if len(strat_ret) > 0 else 0.0

    # 7. Calmar Ratio
    # Annualized Return / |Max Drawdown|
    calmar_ratio = (annualised_return / abs(max_drawdown)) if max_drawdown != 0 else 0.0

    # 8. Total Trades
    # Count number of times position changes
    # A trade is defined as a transition: flat -> long, long -> short, etc.
    # np.diff(pos) != 0 gives us changes.
    total_trades = np.sum(np.diff(pos) != 0)

    return {
        "total_return": float(total_return),
        "annualised_return": float(annualised_return),
        "sharpe_ratio": float(sharpe_ratio),
        "max_drawdown": float(max_drawdown),
        "win_rate": float(win_rate),
        "calmar_ratio": float(calmar_ratio),
        "total_trades": int(total_trades),
        "buy_and_hold_return": float(buy_and_hold_return)
    }

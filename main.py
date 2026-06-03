from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime
import asyncio
import yfinance as yf
from data_fetcher import sync
from bollinger_strategy import apply_bollinger_strategy
from strategy import apply_rsi_strategy, apply_sma_cross_strategy
from metrics import calculate_metrics

app = FastAPI()

def extract_trades(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    trades = []
    current_trade = None

    for i in range(len(results)):
        res = results[i]
        pos = res["position"]
        date = res["date"]
        price = res["price"]

        # Trade close condition: position returns to 0 or reverses
        if current_trade is not None:
            prev_pos = results[i-1]["position"]
            # Position reversed or returned to 0
            if (pos == 0) or (pos != 0 and (pos > 0) != (prev_pos > 0)):
                # Close current trade
                trade = current_trade
                trade["exit_date"] = date
                trade["exit_price"] = price

                # Return Calculation
                if trade["direction"] == "long":
                    trade["return_pct"] = (price / trade["entry_price"]) - 1
                else:
                    trade["return_pct"] = (trade["entry_price"] / price) - 1

                # Duration Calculation
                d1 = datetime.strptime(trade["entry_date"], "%Y-%m-%d")
                d2 = datetime.strptime(trade["exit_date"], "%Y-%m-%d")
                trade["duration_days"] = (d2 - d1).days

                trades.append(trade)
                current_trade = None

        # Trade open condition: position changes from 0 or opposite direction
        if current_trade is None:
            if pos != 0:
                # If we are here, it's either the start of the data or the previous position was 0 (or just closed by reversal)
                current_trade = {
                    "entry_date": date,
                    "entry_price": price,
                    "direction": "long" if pos > 0 else "short"
                }

    # Close any open trade at the end of the period
    if current_trade is not None:
        last_res = results[-1]
        trade = current_trade
        trade["exit_date"] = last_res["date"]
        trade["exit_price"] = last_res["price"]
        if trade["direction"] == "long":
            trade["return_pct"] = (trade["exit_price"] / trade["entry_price"]) - 1
        else:
            trade["return_pct"] = (trade["entry_price"] / trade["exit_price"]) - 1
        d1 = datetime.strptime(trade["entry_date"], "%Y-%m-%d")
        d2 = datetime.strptime(trade["exit_date"], "%Y-%m-%d")
        trade["duration_days"] = (d2 - d1).days
        trades.append(trade)

    return trades

class BacktestRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: Optional[str] = None
    window: int = Field(20, ge=5, le=200)
    std_multiplier: float = Field(2.0, ge=0.5, le=5.0)
    risk_free_rate: float = 0.0
    strategy: Literal["bollinger", "rsi", "sma_cross"] = "bollinger"

    @model_validator(mode='after')
    def check_dates(self) -> 'BacktestRequest':
        if self.start_date and self.end_date:
            try:
                start = datetime.strptime(self.start_date, "%Y-%m-%d")
                end = datetime.strptime(self.end_date, "%Y-%m-%d")
                if start >= end:
                    raise ValueError("start_date must be before end_date")
            except ValueError as e:
                if str(e) == "start_date must be before end_date":
                    raise e
                pass
        return self

class CompareRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: Optional[str] = None
    window: int = Field(20, ge=5, le=200)
    std_multiplier: float = Field(2.0, ge=0.5, le=5.0)
    risk_free_rate: float = 0.0
    strategies: List[str]

    @model_validator(mode='after')
    def validate_strategies(self) -> 'CompareRequest':
        valid_strategies = {"bollinger", "rsi", "sma_cross"}
        for s in self.strategies:
            if s not in valid_strategies:
                raise ValueError(f"Invalid strategy {s}. Must be one of {valid_strategies}")
        return self

    @model_validator(mode='after')
    def check_dates(self) -> 'CompareRequest':
        if self.start_date and self.end_date:
            try:
                start = datetime.strptime(self.start_date, "%Y-%m-%d")
                end = datetime.strptime(self.end_date, "%Y-%m-%d")
                if start >= end:
                    raise ValueError("start_date must be before end_date")
            except ValueError as e:
                if str(e) == "start_date must be before end_date":
                    raise e
                pass
        return self

@app.post("/api/backtest")
async def backtest(request: BacktestRequest):
    try:
        try:
            # Parse dates
            since = datetime.strptime(request.start_date, "%Y-%m-%d")
            till = datetime.strptime(request.end_date, "%Y-%m-%d") if request.end_date else datetime.now()
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {str(ve)}")

        # Fetch data
        raw_data = await sync(request.ticker, "1d", since, till)
        if not raw_data:
            raise HTTPException(status_code=404, detail="No data found for the given ticker and date range")

        # Extract close prices
        close_prices = [d["close"] for d in raw_data]

        # Apply strategy
        if request.strategy == "bollinger":
            results = apply_bollinger_strategy(close_prices, window=request.window, k=request.std_multiplier)
        elif request.strategy == "rsi":
            results = apply_rsi_strategy(close_prices)
        elif request.strategy == "sma_cross":
            results = apply_sma_cross_strategy(close_prices)
        else:
            # This part is technically unreachable due to Literal type check by Pydantic,
            # but included as per explicit user requirement.
            raise HTTPException(status_code=422, detail="Unknown strategy. Choose: bollinger, rsi, sma_cross")

        if not results:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough data to run strategy. Need at least {request.window} bars, got {len(close_prices)}."
            )

        # Calculate metrics
        metrics = calculate_metrics(
            strategy_returns=[r["strategy_return"] for r in results],
            close_prices=[r["price"] for r in results],
            positions=[r["position"] for r in results],
            risk_free_rate=request.risk_free_rate
        )

        trades = extract_trades(results)

        response = {
            "results": results,
            "metrics": metrics,
            "trades": trades
        }

        return response

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compare")
async def compare(request: CompareRequest):
    try:
        try:
            since = datetime.strptime(request.start_date, "%Y-%m-%d")
            till = datetime.strptime(request.end_date, "%Y-%m-%d") if request.end_date else datetime.now()
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {str(ve)}")

        raw_data = await sync(request.ticker, "1d", since, till)
        if not raw_data:
            raise HTTPException(status_code=404, detail="No data found for the given ticker and date range")

        close_prices = [d["close"] for d in raw_data]

        async def run_strategy(strat_name):
            def sync_op():
                if strat_name == "bollinger":
                    res = apply_bollinger_strategy(close_prices, window=request.window, k=request.std_multiplier)
                elif strat_name == "rsi":
                    res = apply_rsi_strategy(close_prices)
                elif strat_name == "sma_cross":
                    res = apply_sma_cross_strategy(close_prices)
                else:
                    return None

                if not res:
                    return None

                metrics = calculate_metrics(
                    strategy_returns=[r["strategy_return"] for r in res],
                    close_prices=[r["price"] for r in res],
                    positions=[r["position"] for r in res],
                    risk_free_rate=request.risk_free_rate
                )
                trades = extract_trades(res)
                return {"results": res, "metrics": metrics, "trades": trades}

            return await asyncio.get_event_loop().run_in_executor(None, sync_op)

        tasks = [run_strategy(s) for s in request.strategies]
        results_list = await asyncio.gather(*tasks)

        final_results = {}
        for strat, res in zip(request.strategies, results_list):
            if res is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Strategy {strat} failed to run. Not enough data for the given window."
                )
            final_results[strat] = res

        return final_results

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ticker/search")
async def search_ticker(q: str):
    fallback_list = [
        {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ"},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "exchange": "NASDAQ"},
        {"symbol": "TSLA", "name": "Tesla Inc.", "exchange": "NASDAQ"},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ"},
        {"symbol": "META", "name": "Meta Platforms Inc.", "exchange": "NASDAQ"},
        {"symbol": "BRK-B", "name": "Berkshire Hathaway Inc.", "exchange": "NYSE"},
    ]

    try:
        search = yf.Search(q, max_results=8)
        quotes = search.quotes

        results = []
        for quote in quotes:
            symbol = quote.get("symbol")
            if symbol:
                results.append({
                    "symbol": symbol,
                    "name": quote.get("shortName", quote.get("longName", "Unknown")),
                    "exchange": quote.get("exchange", "Unknown")
                })

        if results:
            return results[:8]
        return fallback_list

    except Exception:
        return fallback_list

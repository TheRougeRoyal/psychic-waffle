from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal
from datetime import datetime
from data_fetcher import sync
from bollinger_strategy import apply_bollinger_strategy
from strategy import apply_rsi_strategy, apply_sma_cross_strategy
from metrics import calculate_metrics

app = FastAPI()

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
                # We let the date parsing errors handle themselves in the main handler,
                # but Pydantic validators should raise ValueError for validation failure.
                # However, if it's just a format error, we can ignore it here and let
                # the main handler catch it, but for the specific logic:
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

        return {
            "results": results,
            "metrics": metrics
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

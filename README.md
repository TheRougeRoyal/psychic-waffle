# Psychic Waffle

## Overview
A high-performance backtesting web application for evaluating Bollinger Band trading strategies. It provides a seamless bridge between historical market data and visual performance analysis.

## Features
- **Bollinger Band Strategy**: Automated backtesting with customizable period and standard deviation.
- **Comparative Analysis**: Side-by-side comparison of multiple strategy parameters.
- **Interactive Charts**: Visual equity curves and trade markers powered by Recharts.
- **NSE Integration**: Real-time ticker search and data fetching via Yahoo Finance.

## Quick Start
1. `git clone <repo-url>`
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set `SUPABASE_URL` and `SUPABASE_KEY`
4. `cd frontend && npm install && npm run dev`
5. `uvicorn main:app --reload`

The app loads `.env` automatically at startup. If the Supabase values are missing, non-database endpoints still start normally; database routes only fail when they are called.

## Docker Deploy
```bash
docker build -t psychic-waffle .
docker run -p 8000:8000 psychic-waffle
# Open browser at http://localhost:8000
```

## Deploy to Railway
1. Install Railway CLI: `npm i -g @railway/cli`
2. Login: `railway login`
3. Initialize project: `railway init`
4. Deploy: `railway up` (Railway auto-detects Dockerfile)

## API Reference
| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | System health check |
| `/api/backtest` | POST | Execute a single strategy backtest |
| `/api/compare` | POST | Compare multiple strategy configurations |
| `/api/ticker/search` | GET | Search for NSE ticker symbols |

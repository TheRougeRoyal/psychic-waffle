from typing import List, Dict, Tuple
import httpx
import asyncio
import datetime

timeout = 5
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}


class YahooOHLC:
    def __init__(
        self,
        instrument: str,
        granularity: str,
        since: datetime.datetime,
        till: datetime.datetime = None,
    ) -> None:

        self.instrument = instrument
        self.granularity = granularity.lower()
        self.since = int(since.timestamp())

        if till:
            self.till = int(till.timestamp())
        else:
            self.till = int(datetime.datetime.now().timestamp())

        if granularity not in [
            "1m",
            "2m",
            "5m",
            "15m",
            "30m",
            "60m",
            "90m",
            "1h",
            "1d",
            "5d",
            "1wk",
            "1mo",
            "3mo",
        ]:
            raise Exception("Invalid granularity!")

    @property
    def url(self) -> str:
        q = f"""https://query1.finance.yahoo.com/v8/finance/chart/{self.instrument}?symbol={self.instrument}&period1={self.since}&period2={self.till}&interval={self.granularity}&includePrePost=true&events=div%7Csplit%7Cearn&lang=en-US&region=US&crumb=t5QZMhgytYZ&corsDomain=finance.yahoo.com"""
        return q

    def normalize_data(
        self, raw: dict
    ) -> List[Tuple[str, float, float, float, float, float]]:
        """normalize data"""
        return [
            (
                datetime.datetime.fromtimestamp(raw["timestamp"][i]).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                raw["o"][i],
                raw["h"][i],
                raw["l"][i],
                raw["c"][i],
                raw["v"][i],
            )
            for i in range(len(raw["timestamp"]))
        ]


async def sync(
    inst: str, granularity: str, since: datetime.datetime
) -> List[Tuple[str, float, float, float, float, float]]:

    yahoo = YahooOHLC(instrument=inst, granularity=granularity, since=since)

    async with httpx.AsyncClient() as client:
        response = await client.get(yahoo.url, headers=headers, timeout=timeout)

    data = response.json()
    if "chart" not in data or data["chart"].get("error"):
        raise Exception(data.get("chart", {}).get("error", "Unknown Yahoo Finance error"))

    result = data["chart"]["result"][0]
    record = yahoo.normalize_data(
        {
            "timestamp": result["timestamp"],
            "o": result["indicators"]["quote"][0]["open"],
            "h": result["indicators"]["quote"][0]["high"],
            "l": result["indicators"]["quote"][0]["low"],
            "c": result["indicators"]["quote"][0]["close"],
            "v": result["indicators"]["quote"][0]["volume"],
        }
    )

    return record

"""Tiingo EOD raw bars. Requires user-provided entitlement; never stores credentials."""

from datetime import datetime, timezone
import os
import re
import pandas as pd
import requests
from quantlab.data.core import Dataset, sessions


class TiingoProvider:
    def download(self, symbols: list[str], start: str, end: str) -> Dataset:
        token = os.environ.get("TIINGO_API_TOKEN")
        if not token:
            raise ValueError("Export TIINGO_API_TOKEN; see README for provider setup")
        frames = []
        for symbol in symbols:
            if not re.fullmatch(r"[A-Za-z0-9.-]+", symbol):
                raise ValueError("Invalid provider symbol")
            response = requests.get(
                f"https://api.tiingo.com/tiingo/daily/{symbol}/prices",
                headers={"Authorization": f"Token {token}"},
                params={"startDate": start, "endDate": end, "format": "json"},
                timeout=60,
            )
            if response.status_code != 200:
                raise ValueError(f"Tiingo request failed for {symbol}: HTTP {response.status_code}")
            rows = response.json()
            if not isinstance(rows, list) or not rows:
                raise ValueError(f"No daily data returned for {symbol}")
            df = pd.DataFrame(rows).rename(columns={"splitFactor": "split", "divCash": "dividend"})
            # Tiingo UTC midnight is a date label, not an execution timestamp.
            df["date"] = pd.to_datetime(df.date, utc=True).dt.tz_localize(None)
            df["symbol"] = symbol
            if not pd.DatetimeIndex(df.date).equals(sessions(start, end)):
                raise ValueError(f"{symbol}: provider did not supply every requested XNYS session")
            frames.append(
                df[
                    [
                        "date",
                        "symbol",
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                        "split",
                        "dividend",
                    ]
                ]
            )
        return Dataset.create(
            pd.concat(frames, ignore_index=True),
            {
                "provider": "tiingo-eod",
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "request": {"symbols": symbols, "start": start, "end": end},
                "limitations": [
                    "No point-in-time constituents or delisting settlements supplied by this adapter",
                    "Ticker identifiers are not permanent security identifiers",
                    "Revised historical data, not a historical knowledge-vintage archive",
                    "Dividends credited on ex-date, not payment date; approximate cash availability",
                ],
            },
        )

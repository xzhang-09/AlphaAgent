from __future__ import annotations

import re


COMMON_TICKER_CORRECTIONS = {
    "APPL": "AAPL",
}


def normalize_ticker(raw_ticker: str) -> str:
    return raw_ticker.strip().upper()


def suggest_ticker_correction(raw_ticker: str) -> str | None:
    ticker = normalize_ticker(raw_ticker)
    return COMMON_TICKER_CORRECTIONS.get(ticker)


def is_valid_ticker_format(raw_ticker: str) -> bool:
    ticker = normalize_ticker(raw_ticker)
    if not ticker:
        return False
    return bool(re.fullmatch(r"[A-Z0-9.\-=\^]+", ticker))

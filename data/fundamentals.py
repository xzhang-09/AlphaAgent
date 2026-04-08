from __future__ import annotations

from data.clients import FundamentalsClient


class FundamentalsAdapter:
    def __init__(self) -> None:
        self.client = FundamentalsClient()

    def get_fundamentals_snapshot(self, ticker: str) -> dict:
        return self.client.get_financials(ticker)

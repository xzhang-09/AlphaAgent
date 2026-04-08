from __future__ import annotations

from data.clients import FilingsClient


class FilingsLoader:
    def __init__(self) -> None:
        self.client = FilingsClient()

    def load(self, ticker: str) -> list[dict]:
        try:
            return self.client.get_filings(ticker)
        except Exception:
            return []

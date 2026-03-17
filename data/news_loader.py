from __future__ import annotations

from data.clients import NewsClient


class NewsLoader:
    def __init__(self) -> None:
        self.client = NewsClient()

    def load(self, ticker: str) -> list[dict]:
        try:
            return self.client.get_news(ticker)
        except Exception:
            return []

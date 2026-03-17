from __future__ import annotations

from data.clients import NewsClient
from data.market_data import MarketDataAdapter


class AsiaNewsLoader:
    def __init__(self) -> None:
        self.news_client = NewsClient()
        self.market_data = MarketDataAdapter()

    def load(self, ticker: str) -> list[dict]:
        try:
            profile = self.market_data.get_company_profile(ticker)
            if profile["region"] == "United States":
                return []
            return self.news_client.search_news(
                query=f"{profile['company_name']} {profile['region']} sector outlook",
                namespace=f"{ticker.upper()}-asia-news",
            )
        except Exception:
            return []

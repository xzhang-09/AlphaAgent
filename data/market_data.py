from __future__ import annotations

from data.clients import MacroDataClient, MarketDataClient


class MarketDataAdapter:
    def __init__(self) -> None:
        self.client = MarketDataClient()
        self.macro_client = MacroDataClient()

    def get_market_snapshot(self, ticker: str) -> dict:
        return self.client.get_snapshot(ticker)

    def get_peer_snapshot(self, ticker: str) -> list[dict]:
        return []

    def get_company_profile(self, ticker: str) -> dict:
        return self.client.get_company_profile(ticker)

    def get_macro_snapshot(self, ticker: str) -> dict:
        profile = self.get_company_profile(ticker)
        return self.macro_client.get_macro_snapshot(profile=profile, ticker=ticker)

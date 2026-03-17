from __future__ import annotations

from data.clients import MarketDataClient


class MarketDataAdapter:
    def __init__(self) -> None:
        self.client = MarketDataClient()

    def get_market_snapshot(self, ticker: str) -> dict:
        return self.client.get_snapshot(ticker)

    def get_peer_snapshot(self, ticker: str) -> list[dict]:
        return []

    def get_company_profile(self, ticker: str) -> dict:
        return self.client.get_company_profile(ticker)

    def get_macro_snapshot(self, ticker: str) -> dict:
        profile = self.get_company_profile(ticker)
        return {
            "macro_summary": f"Macro context for {profile['company_name']} is inferred from its primary region and sector.",
            "fx_summary": f"{profile['currency']} exposure should be monitored versus USD and relevant regional crosses.",
            "rates_summary": "Rates and liquidity conditions can influence valuation multiples and financing conditions.",
            "currency_sensitivity_notes": f"{profile['company_name']} may have FX sensitivity through reporting currency and cost base.",
            "asia_pacific_angle": (
                "Asia-Pacific context should be considered for supply chains, end demand, and regional policy spillovers."
                if profile["region"] != "United States"
                else "Asia-Pacific demand may still matter through supply-chain linkages and end-market exposure."
            ),
            "macro_risk": "Macro slowdown or tighter financial conditions could pressure expectations.",
        }

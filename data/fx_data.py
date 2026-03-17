from __future__ import annotations

from data.clients import MarketDataClient


FX_REFERENCES = {
    "USD": {"USDJPY": "JPY=X", "USDCNH": "CNH=X", "USDHKD": "HKD=X"},
    "TWD": {"USDTWD": "TWD=X", "USDJPY": "JPY=X", "USDKRW": "KRW=X", "USDCNH": "CNH=X"},
    "HKD": {"USDHKD": "HKD=X", "USDCNH": "CNH=X", "USDJPY": "JPY=X"},
    "JPY": {"USDJPY": "JPY=X", "USDCNH": "CNH=X", "USDKRW": "KRW=X"},
    "KRW": {"USDKRW": "KRW=X", "USDJPY": "JPY=X", "USDCNH": "CNH=X"},
    "SGD": {"USDSGD": "SGD=X", "USDCNH": "CNH=X", "USDJPY": "JPY=X"},
}


class FXDataAdapter:
    def __init__(self) -> None:
        self.market_client = MarketDataClient()

    def get_fx_snapshot(self, ticker: str) -> dict:
        profile = self.market_client.get_company_profile(ticker)
        currency = profile["currency"]
        commentary = f"Monitor {currency} against USD and major Asia FX crosses."
        references = FX_REFERENCES.get(currency, FX_REFERENCES["USD"])
        live_pairs = {}
        for label, symbol in references.items():
            try:
                live_pairs[label] = round(self.market_client.get_quote_value(symbol), 4)
            except Exception:
                continue
        return {
            "reporting_currency": currency,
            "reference_pairs": live_pairs,
            "regional_fx_commentary": commentary,
        }

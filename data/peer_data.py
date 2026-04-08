from __future__ import annotations

from config.settings import get_settings
from data.clients import MarketDataClient, _damodaran_industry_snapshot, _fmp_stock_peers


CURATED_PEERS = {
    "NVDA": ["AMD", "AVGO", "TSM"],
    "AMD": ["NVDA", "INTC", "AVGO"],
    "TSM": ["ASML", "005930.KS", "INTC"],
    "AAPL": ["MSFT", "GOOGL", "SONY"],
    "MSFT": ["GOOGL", "ORCL", "AMZN"],
    "META": ["GOOGL", "SNAP", "BABA"],
    "TSLA": ["BYDDY", "TM", "RIVN"],
    "BABA": ["0700.HK", "JD", "PDD"],
    "0700.HK": ["BABA", "PDD", "NTES"],
}


class PeerDataAdapter:
    def __init__(self) -> None:
        self.market_client = MarketDataClient()
        self.settings = get_settings()

    def get_peer_snapshot(self, ticker: str) -> list[dict]:
        ticker = ticker.upper()
        profile = self.market_client.get_company_profile(ticker)
        peers = []
        if self.settings.fmp_api_key:
            peers = _fmp_stock_peers(ticker, self.settings.fmp_api_key)
        if not peers:
            peers = CURATED_PEERS.get(ticker, [])
        snapshots = []
        for peer in peers[:5]:
            if peer == ticker:
                continue
            try:
                market = self.market_client.get_snapshot(peer)
                snapshots.append(
                    {
                        "ticker": peer,
                        "forward_pe": _round_or_none(market.get("forward_pe")),
                        "ev_ebitda": _round_or_none(market.get("ev_ebitda")),
                        "revenue_growth_yoy": _round_or_none(float(market.get("info", {}).get("revenueGrowth", 0.0) * 100)),
                        "source": "fmp_stock_peers" if self.settings.fmp_api_key else "curated_peer_map",
                    }
                )
            except Exception:
                continue
            if len(snapshots) >= 3:
                break

        benchmark = _damodaran_industry_snapshot(
            sector=profile.get("sector", ""),
            industry=profile.get("industry", ""),
        )
        if benchmark:
            snapshots.append(
                {
                    "ticker": "INDUSTRY_MEDIAN",
                    "forward_pe": _round_or_none(benchmark.get("forward_pe")),
                    "ev_ebitda": _round_or_none(benchmark.get("ev_ebitda")),
                    "revenue_growth_yoy": None,
                    "source": benchmark.get("source", "damodaran_compdata"),
                    "label": benchmark.get("matched_industry"),
                }
            )

        return snapshots


def _round_or_none(value):
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None

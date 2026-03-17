from __future__ import annotations

from data.clients import MarketDataClient


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

    def get_peer_snapshot(self, ticker: str) -> list[dict]:
        ticker = ticker.upper()
        peers = CURATED_PEERS.get(ticker, [])
        snapshots = []
        for peer in peers[:3]:
            try:
                market = self.market_client.get_snapshot(peer)
                snapshots.append(
                    {
                        "ticker": peer,
                        "forward_pe": round(float(market["forward_pe"]), 2),
                        "ev_ebitda": round(float(market["ev_ebitda"]), 2),
                        "revenue_growth_yoy": round(float(market.get("info", {}).get("revenueGrowth", 0.0) * 100), 1),
                    }
                )
            except Exception:
                continue

        if snapshots:
            return snapshots
        return []

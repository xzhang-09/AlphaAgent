from __future__ import annotations

from agents.signal_agent import SignalDetectionAgent
from config.settings import get_settings
from data.fundamentals import FundamentalsAdapter
from data.market_data import MarketDataAdapter
from schemas.memo import AnalystFeedback
from schemas.research_state import ResearchState


class OpportunityPipeline:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.market_data = MarketDataAdapter()
        self.fundamentals = FundamentalsAdapter()
        self.signal_agent = SignalDetectionAgent()

    def screen(self, tickers: list[str] | None = None) -> list[dict]:
        universe = tickers or self.settings.opportunity_universe
        candidates = []
        for ticker in universe:
            state = ResearchState(
                ticker=ticker,
                analyst_feedback=AnalystFeedback(),
                company_profile=self.market_data.get_company_profile(ticker),
                market_snapshot=self.market_data.get_market_snapshot(ticker),
                fundamentals_snapshot=self.fundamentals.get_fundamentals_snapshot(ticker),
            )
            state = self.signal_agent.run(state)
            summary = state["signal_output"]
            candidates.append(
                {
                    "ticker": ticker,
                    "company_name": state["company_profile"]["company_name"],
                    "score": summary["composite_score"],
                    "why_now": summary["why_now"],
                    "signals": summary,
                }
            )
        return sorted(candidates, key=lambda item: item["score"], reverse=True)


def screen_opportunities(tickers: list[str] | None = None) -> list[dict]:
    return OpportunityPipeline().screen(tickers=tickers)

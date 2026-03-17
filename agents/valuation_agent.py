from __future__ import annotations

from agents.base import BaseAgent
from engine.valuation_model import ValuationModel
from schemas.research_state import ResearchState


class ValuationAgent(BaseAgent):
    name = "valuation_agent"
    output_key = "valuation_output"
    state_alias_key = "valuation_summary"

    def __init__(self) -> None:
        self.model = ValuationModel()

    def analyze(self, state: ResearchState) -> dict:
        market = state["market_snapshot"]
        fundamentals = state["fundamentals_snapshot"]
        return self.model.run(market=market, fundamentals=fundamentals)

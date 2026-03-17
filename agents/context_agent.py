from __future__ import annotations

from agents.base import BaseAgent
from schemas.research_state import ResearchState


class ContextAgent(BaseAgent):
    name = "context_agent"
    output_key = "context_output"
    state_alias_key = "context_summary"

    def analyze(self, state: ResearchState) -> dict:
        market = state["market_snapshot"]
        peer_data = state["peer_snapshot"]

        return {
            "sector_trend_summary": market["sector_trend_summary"],
            "peer_comparison": peer_data,
            "peer_takeaway": (
                f"{state['company_profile']['ticker']} screens against {len(peer_data)} relevant peers on forward multiples and growth."
            ),
        }

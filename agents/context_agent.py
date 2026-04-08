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
        benchmark_count = len([peer for peer in peer_data if peer.get("ticker") == "INDUSTRY_MEDIAN"])
        live_peer_count = len(peer_data) - benchmark_count

        return {
            "sector_trend_summary": market["sector_trend_summary"],
            "peer_comparison": peer_data,
            "peer_takeaway": (
                f"{state['company_profile']['ticker']} screens against {live_peer_count} company peers"
                f"{' plus a Damodaran industry benchmark' if benchmark_count else ''} on forward multiples and growth."
            ),
        }

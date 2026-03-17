from __future__ import annotations

from agents.base import BaseAgent
from schemas.research_state import ResearchState


class RiskAgent(BaseAgent):
    name = "risk_agent"
    output_key = "risk_output"
    state_alias_key = "risk_summary"

    def analyze(self, state: ResearchState) -> dict:
        snapshot = state["fundamentals_snapshot"]
        market = state["market_snapshot"]
        macro = state["macro_snapshot"]

        return {
            "competition": snapshot["risk_factors"]["competition"],
            "regulation": snapshot["risk_factors"]["regulation"],
            "macro_risk": macro["macro_risk"],
            "execution_risk": snapshot["risk_factors"]["execution"],
            "valuation_compression": (
                f"If the multiple compresses from {market['forward_pe']:.1f}x to {market['stress_pe']:.1f}x,"
                " downside could overwhelm earnings delivery."
            ),
            "factor_style_exposure": market["factor_style_exposure"],
        }

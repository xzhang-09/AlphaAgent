from __future__ import annotations

from agents.base import BaseAgent
from schemas.research_state import ResearchState


class MacroAgent(BaseAgent):
    name = "macro_agent"
    output_key = "macro_output"
    state_alias_key = "macro_summary"

    def analyze(self, state: ResearchState) -> dict:
        macro = state["macro_snapshot"]
        fx = state["fx_snapshot"]
        company = state["company_profile"]

        fx_pairs = [f"{pair}: {value}" for pair, value in fx["reference_pairs"].items()]
        sensitivity = macro.get("currency_sensitivity_notes") or (
            f"{company['company_name']} has limited direct FX sensitivity based on currently available live currency data."
        )

        return {
            "sector_backdrop": macro["macro_summary"],
            "rates_context": macro["rates_summary"],
            "fx_context": fx["regional_fx_commentary"],
            "regional_context": macro["asia_pacific_angle"],
            "reference_pairs": fx_pairs,
            "currency_sensitivity": sensitivity,
            "macro_risk": macro["macro_risk"],
        }

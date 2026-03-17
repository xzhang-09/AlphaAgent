from __future__ import annotations

from agents.base import BaseAgent
from schemas.research_state import ResearchState
from utils.llm import LLMClient


class FundamentalResearchAgent(BaseAgent):
    name = "fundamental_agent"
    output_key = "fundamental_output"
    state_alias_key = "fundamental_summary"

    def __init__(self) -> None:
        self.llm = LLMClient()

    def analyze(self, state: ResearchState) -> dict:
        snapshot = state["fundamentals_snapshot"]
        rag = state["rag_context"]

        transcript_notes = [doc["snippet"] for doc in rag["transcript_docs"][:2]] or [
            "No live earnings transcript was retrieved for the current run."
        ]
        filing_notes = [doc["snippet"] for doc in rag["filing_docs"][:2]] or [
            "No live filing excerpt was retrieved for the current run."
        ]
        fallback = {
            "business_overview": snapshot["business_overview"],
            "revenue_margin_trends": {
                "revenue_growth_yoy": snapshot["revenue_growth_yoy"],
                "prior_revenue_growth_yoy": snapshot["prior_revenue_growth_yoy"],
                "gross_margin": snapshot["gross_margin"],
                "ebit_margin": snapshot["ebit_margin"],
                "prior_ebit_margin": snapshot["prior_ebit_margin"],
                "summary": (
                    f"Revenue growth is {snapshot['revenue_growth_yoy']:.1f}% and EBIT margin is "
                    f"{snapshot['ebit_margin']:.1f}% based on live financial data."
                ),
            },
            "cash_flow_quality": {
                "fcf_margin": snapshot["fcf_margin"],
                "cash_conversion": snapshot["cash_conversion"],
                "commentary": snapshot["cash_flow_commentary"],
            },
            "key_business_drivers": snapshot["key_business_drivers"],
            "management_commentary": transcript_notes,
            "filing_support": filing_notes,
        }
        llm_payload = self.llm.generate_json(
            prompt=(
                f"You are a buy-side fundamental analyst covering {state['company_profile']['company_name']} ({state['ticker']}). "
                "Use the live financial data and retrieved documents below to write a concise JSON summary with these keys: "
                "business_overview, revenue_margin_summary, cash_flow_commentary, key_business_drivers, management_commentary, filing_support. "
                "Keep key_business_drivers, management_commentary, and filing_support as arrays of short strings.\n\n"
                f"Live fundamentals: {snapshot}\n"
                f"Transcript evidence: {transcript_notes}\n"
                f"Filing evidence: {filing_notes}\n"
            ),
            fallback={
                "business_overview": fallback["business_overview"],
                "revenue_margin_summary": fallback["revenue_margin_trends"]["summary"],
                "cash_flow_commentary": fallback["cash_flow_quality"]["commentary"],
                "key_business_drivers": fallback["key_business_drivers"],
                "management_commentary": fallback["management_commentary"],
                "filing_support": fallback["filing_support"],
            },
        )
        if not isinstance(llm_payload, dict):
            llm_payload = {}

        return {
            **fallback,
            "business_overview": llm_payload.get("business_overview") or fallback["business_overview"],
            "revenue_margin_trends": {
                **fallback["revenue_margin_trends"],
                "summary": llm_payload.get("revenue_margin_summary") or fallback["revenue_margin_trends"]["summary"],
            },
            "cash_flow_quality": {
                **fallback["cash_flow_quality"],
                "commentary": llm_payload.get("cash_flow_commentary") or fallback["cash_flow_quality"]["commentary"],
            },
            "key_business_drivers": llm_payload.get("key_business_drivers") or fallback["key_business_drivers"],
            "management_commentary": llm_payload.get("management_commentary") or fallback["management_commentary"],
            "filing_support": llm_payload.get("filing_support") or fallback["filing_support"],
        }

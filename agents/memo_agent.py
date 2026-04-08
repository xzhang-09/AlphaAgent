from __future__ import annotations

from agents.base import BaseAgent
from schemas.memo import MemoContent, MemoSection
from schemas.research_state import ResearchState
from utils.llm import LLMClient


class MemoAgent(BaseAgent):
    name = "memo_agent"
    output_key = "memo_output"
    state_alias_key = "memo_draft"

    def __init__(self) -> None:
        self.llm = LLMClient()

    def analyze(self, state: ResearchState) -> MemoContent:
        company = state["company_profile"]
        signal = state["signal_output"]
        fundamentals = state["fundamental_output"]
        context = state["context_output"]
        macro = state["macro_output"]
        valuation = state["valuation_output"]
        risk = state["risk_output"]
        feedback = state.get("analyst_feedback", {})

        feedback_bull = feedback.get("bull_case", "").strip()
        feedback_bear = feedback.get("bear_case", "").strip()
        feedback_catalysts = feedback.get("catalysts", "").strip()
        valuation_supported = valuation.get("valuation_supported", False)
        scenario_analysis = valuation.get("scenario_analysis", {})
        base_case = scenario_analysis.get("base", {})
        bull_scenario = scenario_analysis.get("bull", {})

        bull_case = feedback_bull or bull_scenario.get(
            "thesis",
            "Bull case depends on earnings durability, multiple support, and execution against guidance.",
        )
        bear_case = feedback_bear or risk["competition"]
        catalysts = feedback_catalysts or "; ".join(company["catalysts"])
        valuation_prompt_fragment = (
            f"Base target: {base_case['target_price']:.2f}. "
            if valuation_supported and base_case.get("target_price") is not None
            else "Valuation target was not generated because benchmark multiples were insufficient. "
        )
        llm_conclusion = self.llm.generate(
            prompt=(
                f"Write a concise buy-side investment memo conclusion for {company['company_name']} ({company['ticker']}). "
                f"Why now: {signal['why_now']}. {valuation_prompt_fragment}"
                f"Main risk: {risk['macro_risk']}. Keep it to two sentences and frame as decision support, not a trading command."
            ),
            fallback=(
                "The setup supports further PM attention, but sizing should depend on conviction "
                "in earnings durability and risk-reward versus peers."
            ),
        )
        valuation_summary = (
            f"Current price is {valuation['current_price']:.2f}. Base-case target is "
            f"{base_case['target_price']:.2f}, implying "
            f"{base_case['upside_pct']:.1f}% upside."
            if valuation_supported and base_case.get("target_price") is not None and base_case.get("upside_pct") is not None
            else valuation.get("support_summary", "Valuation scenario analysis was not generated for this run.")
        )
        valuation_bullets = [
            f"Forward P/E: {valuation['relative_valuation']['forward_pe']:.1f}x"
            if valuation["relative_valuation"].get("forward_pe") is not None
            else "Forward P/E: N/A",
            f"Peer P/E: {valuation['relative_valuation']['peer_forward_pe']:.1f}x"
            if valuation["relative_valuation"].get("peer_forward_pe") is not None
            else "Peer P/E: N/A",
            f"EV/EBITDA: {valuation['relative_valuation']['ev_ebitda']:.1f}x"
            if valuation["relative_valuation"].get("ev_ebitda") is not None
            else "EV/EBITDA: N/A",
        ]

        return MemoContent(
            title=f"PM Memo: {company['company_name']} ({company['ticker']})",
            company=MemoSection(
                heading="Company / Ticker / Sector",
                bullets=[
                    f"Company: {company['company_name']}",
                    f"Ticker: {company['ticker']}",
                    f"Sector: {company['sector']}",
                    f"Region: {company['region']}",
                ],
            ),
            why_now=MemoSection(
                heading="Why Now",
                summary=(
                    f"{signal['why_now']} Composite score is {signal['composite_score']:.0f}/100. "
                    f"Revenue growth is {fundamentals['revenue_margin_trends']['revenue_growth_yoy']:.1f}% "
                    f"and EBIT margin is {fundamentals['revenue_margin_trends']['ebit_margin']:.1f}%."
                ),
            ),
            key_drivers=MemoSection(
                heading="Key Drivers",
                bullets=[
                    fundamentals["key_business_drivers"][0],
                    fundamentals["key_business_drivers"][1],
                    fundamentals["management_commentary"][0],
                ],
            ),
            sector_context=MemoSection(
                heading="Sector Context",
                summary=context["sector_trend_summary"],
                bullets=[context["peer_takeaway"]],
            ),
            macro_context=MemoSection(
                heading="Macro / FX / Regional Context",
                summary=macro["sector_backdrop"],
                bullets=[
                    f"Rates: {macro['rates_context']}",
                    f"FX: {macro['fx_context']}",
                    f"Regional context: {macro['regional_context']}",
                    f"Currency sensitivity: {macro['currency_sensitivity']}",
                ],
            ),
            fundamental_analysis=MemoSection(
                heading="Fundamental Analysis",
                summary=f"Business overview: {fundamentals['business_overview']}",
                bullets=[
                    f"FCF margin at {fundamentals['cash_flow_quality']['fcf_margin']:.1f}%",
                    f"Cash conversion at {fundamentals['cash_flow_quality']['cash_conversion']:.1f}%",
                    fundamentals["cash_flow_quality"]["commentary"],
                ],
            ),
            valuation_analysis=MemoSection(
                heading="Valuation Analysis",
                summary=valuation_summary,
                bullets=valuation_bullets,
            ),
            bull_case=MemoSection(heading="Bull Case", summary=bull_case),
            bear_case=MemoSection(heading="Bear Case", summary=bear_case),
            catalysts=MemoSection(heading="Catalysts", summary=catalysts),
            risks=MemoSection(
                heading="Risks",
                bullets=[
                    f"Competition: {risk['competition']}",
                    f"Regulation: {risk['regulation']}",
                    f"Macro: {risk['macro_risk']}",
                    f"Execution: {risk['execution_risk']}",
                ],
            ),
            conclusion=MemoSection(
                heading="Conclusion",
                summary=llm_conclusion,
            ),
        )

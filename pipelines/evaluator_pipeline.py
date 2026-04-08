from __future__ import annotations

import re

from engine.memo_formatter import MemoFormatter


class EvaluatorPipeline:
    def __init__(self) -> None:
        self.formatter = MemoFormatter()

    def run(self, state: dict) -> dict:
        memo = self.formatter.render_markdown(state["memo_output"])
        valuation = state["valuation_output"]
        fundamentals = state["fundamental_output"]
        citations = [citation.model_dump() if hasattr(citation, "model_dump") else citation for citation in state["citations"]]

        expected_numbers = {
            "revenue_growth": fundamentals["revenue_margin_trends"]["revenue_growth_yoy"],
            "ebit_margin": fundamentals["revenue_margin_trends"]["ebit_margin"],
            "current_price": valuation["current_price"],
        }
        if valuation.get("valuation_supported"):
            base_case = valuation.get("scenario_analysis", {}).get("base", {})
            if base_case.get("target_price") is not None:
                expected_numbers["target_price"] = base_case["target_price"]

        mismatches = []
        extracted_numbers = [float(match) for match in re.findall(r"\b\d+\.\d+\b", memo)]
        for label, expected in expected_numbers.items():
            rounded_expected = round(float(expected), 1)
            if not any(abs(number - rounded_expected) < 0.2 for number in extracted_numbers):
                mismatches.append(f"{label}={rounded_expected} missing or inconsistent in memo.")

        hallucination_flags = []
        if "black-box" in memo.lower():
            hallucination_flags.append("Memo framing should avoid suggesting direct prediction or black-box trading.")
        if len(citations) < 2:
            hallucination_flags.append("Citation coverage is too thin for the memo claims.")
        if not valuation.get("valuation_supported") and "base-case target" in memo.lower():
            hallucination_flags.append("Memo references a valuation target even though benchmark valuation support was unavailable.")

        return {
            "numerical_mismatches": mismatches,
            "hallucination_flags": hallucination_flags,
            "citation_metadata": citations,
            "passed": not mismatches and not hallucination_flags,
        }

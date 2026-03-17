from __future__ import annotations

from agents.base import BaseAgent
from engine.memo_formatter import MemoFormatter
from schemas.research_state import ResearchState
from utils.llm import LLMClient


class CriticAgent(BaseAgent):
    name = "critic_agent"
    output_key = "critic_output"
    state_alias_key = "critique_notes"

    def __init__(self) -> None:
        self.formatter = MemoFormatter()
        self.llm = LLMClient()

    def analyze(self, state: ResearchState) -> dict:
        heuristic_issues: list[dict[str, str]] = []
        memo = self.formatter.render_markdown(state["memo_output"])
        valuation = state["valuation_output"]
        citations = state["citations"]

        if len(citations) < 3:
            heuristic_issues.append(
                {
                    "severity": "medium",
                    "target": "fundamental_agent",
                    "issue": "Memo has too few supporting citations for a PM-ready draft.",
                }
            )
        if valuation["scenario_analysis"]["base"]["upside_pct"] > 30 and "Risks" not in memo:
            heuristic_issues.append(
                {
                    "severity": "high",
                    "target": "risk_agent",
                    "issue": "High-upside case is not balanced by an explicit risks section.",
                }
            )
        if "currency" not in memo.lower() and state["company_profile"]["region"] != "United States":
            heuristic_issues.append(
                {
                    "severity": "medium",
                    "target": "macro_agent",
                    "issue": "Asia-Pacific name is missing explicit currency sensitivity discussion.",
                }
            )

        llm_payload = self.llm.generate_json(
            prompt=(
                "You are a red-team critic reviewing a buy-side PM memo. "
                "Return JSON with a single key 'issues', whose value is an array of objects with keys "
                "severity, target, and issue. Valid targets are fundamental_agent, context_agent, macro_agent, risk_agent, memo_agent. "
                "Only flag genuine unsupported claims, missing risks, weak evidence, or data conflicts.\n\n"
                f"Memo markdown:\n{memo}\n\n"
                f"Valuation summary: {valuation}\n"
                f"Citation count: {len(citations)}\n"
                f"Citation titles: {[citation.title if hasattr(citation, 'title') else citation.get('title', '') for citation in citations]}\n"
            ),
            fallback={"issues": heuristic_issues},
        )
        issues = llm_payload.get("issues") if isinstance(llm_payload, dict) else heuristic_issues
        valid_targets = {"fundamental_agent", "context_agent", "macro_agent", "risk_agent", "memo_agent"}
        cleaned_issues = []
        for issue in issues or []:
            target = issue.get("target") if isinstance(issue, dict) else None
            if target not in valid_targets:
                target = "memo_agent"
            cleaned_issues.append(
                {
                    "severity": issue.get("severity", "medium") if isinstance(issue, dict) else "medium",
                    "target": target,
                    "issue": issue.get("issue", "") if isinstance(issue, dict) else str(issue),
                }
            )

        needs_refinement = bool(cleaned_issues) and state["refinement_count"] < state["max_refinements"]
        target = cleaned_issues[0]["target"] if cleaned_issues else None

        return {
            "issues": cleaned_issues,
            "needs_refinement": needs_refinement,
            "refinement_target": target,
        }

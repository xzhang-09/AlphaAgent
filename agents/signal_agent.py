from __future__ import annotations

from agents.base import BaseAgent
from schemas.research_state import ResearchState
from schemas.signals import CandidateIdea, SignalItem, SignalSummary
from utils.scoring import bounded_score


class SignalDetectionAgent(BaseAgent):
    name = "signal_agent"
    output_key = "signal_output"
    state_alias_key = "signals"

    def analyze(self, state: ResearchState) -> SignalSummary:
        market = state["market_snapshot"]
        fundamentals = state["fundamentals_snapshot"]

        event_signals: list[SignalItem] = []
        if fundamentals["earnings_surprise_pct"] > 5:
            event_signals.append(
                SignalItem(
                    signal_type="event",
                    description=f"Earnings surprise of {fundamentals['earnings_surprise_pct']:.1f}% vs consensus.",
                    strength=0.9,
                )
            )
        if fundamentals.get("management_change"):
            event_signals.append(
                SignalItem(
                    signal_type="event",
                    description=f"Management change: {fundamentals['management_change']}.",
                    strength=0.6,
                )
            )
        if fundamentals.get("regulatory_event"):
            event_signals.append(
                SignalItem(
                    signal_type="event",
                    description=f"Regulatory event: {fundamentals['regulatory_event']}.",
                    strength=0.7,
                )
            )

        valuation_signals: list[SignalItem] = []
        if market["forward_pe"] < market["peer_forward_pe"]:
            valuation_signals.append(
                SignalItem(
                    signal_type="valuation",
                    description=f"Forward P/E of {market['forward_pe']:.1f}x trades below peer average of {market['peer_forward_pe']:.1f}x.",
                    strength=0.7,
                )
            )
        if market["historical_pe_percentile"] < 50:
            valuation_signals.append(
                SignalItem(
                    signal_type="valuation",
                    description=f"Valuation is at the {market['historical_pe_percentile']:.0f}th historical percentile.",
                    strength=0.6,
                )
            )

        fundamental_signals: list[SignalItem] = []
        if fundamentals["revenue_growth_yoy"] > fundamentals["prior_revenue_growth_yoy"]:
            fundamental_signals.append(
                SignalItem(
                    signal_type="fundamental",
                    description=f"Revenue growth accelerated to {fundamentals['revenue_growth_yoy']:.1f}% from {fundamentals['prior_revenue_growth_yoy']:.1f}%.",
                    strength=0.8,
                )
            )
        if fundamentals["ebit_margin"] > fundamentals["prior_ebit_margin"]:
            fundamental_signals.append(
                SignalItem(
                    signal_type="fundamental",
                    description=f"EBIT margin improved to {fundamentals['ebit_margin']:.1f}% from {fundamentals['prior_ebit_margin']:.1f}%.",
                    strength=0.8,
                )
            )

        market_signals: list[SignalItem] = []
        if market["drawdown_pct"] <= -15:
            market_signals.append(
                SignalItem(
                    signal_type="market",
                    description=f"Shares are down {abs(market['drawdown_pct']):.1f}% from the recent high.",
                    strength=0.6,
                )
            )
        if market["volume_spike_ratio"] >= 1.5:
            market_signals.append(
                SignalItem(
                    signal_type="market",
                    description=f"Volume spike at {market['volume_spike_ratio']:.1f}x normal trading volume.",
                    strength=0.5,
                )
            )

        composite_score = bounded_score(
            [
                len(event_signals) * 20,
                len(valuation_signals) * 20,
                len(fundamental_signals) * 20,
                len(market_signals) * 15,
            ]
        )

        why_now = (
            "Signal stack is strongest around earnings revision, margin trajectory, and valuation context."
            if composite_score >= 70
            else "Signal stack is mixed but still actionable for analyst review."
        )

        return SignalSummary(
            candidate=composite_score >= 45,
            composite_score=composite_score,
            why_now=why_now,
            ranked_candidates=[
                CandidateIdea(
                    ticker=state["ticker"],
                    score=composite_score,
                    reason=why_now,
                )
            ],
            event_signals=event_signals,
            valuation_signals=valuation_signals,
            fundamental_signals=fundamental_signals,
            market_signals=market_signals,
        )

from __future__ import annotations

from typing import Any

from pydantic import Field

from schemas.base import DictLikeModel
from schemas.memo import AnalystFeedback, MemoContent
from schemas.signals import Citation, SignalSummary


class ResearchState(DictLikeModel):
    ticker: str
    analyst_feedback: AnalystFeedback = Field(default_factory=AnalystFeedback)
    company_profile: dict[str, Any] = Field(default_factory=dict)
    market_snapshot: dict[str, Any] = Field(default_factory=dict)
    fundamentals_snapshot: dict[str, Any] = Field(default_factory=dict)
    peer_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    macro_snapshot: dict[str, Any] = Field(default_factory=dict)
    fx_snapshot: dict[str, Any] = Field(default_factory=dict)
    rag_context: dict[str, Any] = Field(default_factory=dict)
    citations: list[Citation] = Field(default_factory=list)

    signals: SignalSummary | None = None
    signal_output: SignalSummary | None = None
    opportunity_output: dict[str, Any] = Field(default_factory=dict)
    fundamental_summary: dict[str, Any] = Field(default_factory=dict)
    fundamental_output: dict[str, Any] = Field(default_factory=dict)
    context_summary: dict[str, Any] = Field(default_factory=dict)
    context_output: dict[str, Any] = Field(default_factory=dict)
    macro_summary: dict[str, Any] = Field(default_factory=dict)
    macro_output: dict[str, Any] = Field(default_factory=dict)
    valuation_summary: dict[str, Any] = Field(default_factory=dict)
    valuation_output: dict[str, Any] = Field(default_factory=dict)
    risk_summary: dict[str, Any] = Field(default_factory=dict)
    risk_output: dict[str, Any] = Field(default_factory=dict)
    memo_draft: MemoContent | None = None
    memo_output: MemoContent | None = None
    critique_notes: dict[str, Any] = Field(default_factory=dict)
    critic_output: dict[str, Any] = Field(default_factory=dict)
    evaluator_output: dict[str, Any] = Field(default_factory=dict)
    final_output: dict[str, Any] = Field(default_factory=dict)

    refinement_count: int = 0
    max_refinements: int = 2
    status_log: list[str] = Field(default_factory=list)

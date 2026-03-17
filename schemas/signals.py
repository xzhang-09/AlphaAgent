from __future__ import annotations

from pydantic import Field

from schemas.base import DictLikeModel


class Citation(DictLikeModel):
    citation_id: str
    source_type: str
    title: str
    snippet: str


class SignalItem(DictLikeModel):
    signal_type: str
    description: str
    strength: float = 1.0


class CandidateIdea(DictLikeModel):
    ticker: str
    score: float
    reason: str


class SignalSummary(DictLikeModel):
    candidate: bool
    composite_score: float
    why_now: str
    ranked_candidates: list[CandidateIdea] = Field(default_factory=list)
    event_signals: list[SignalItem] = Field(default_factory=list)
    valuation_signals: list[SignalItem] = Field(default_factory=list)
    fundamental_signals: list[SignalItem] = Field(default_factory=list)
    market_signals: list[SignalItem] = Field(default_factory=list)

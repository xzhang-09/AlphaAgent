from __future__ import annotations

from pydantic import Field

from schemas.base import DictLikeModel


class AnalystFeedback(DictLikeModel):
    bull_case: str = ""
    bear_case: str = ""
    catalysts: str = ""
    notes: str = ""


class MemoSection(DictLikeModel):
    heading: str
    summary: str = ""
    bullets: list[str] = Field(default_factory=list)


class MemoContent(DictLikeModel):
    title: str
    company: MemoSection
    why_now: MemoSection
    key_drivers: MemoSection
    sector_context: MemoSection
    macro_context: MemoSection
    fundamental_analysis: MemoSection
    valuation_analysis: MemoSection
    bull_case: MemoSection
    bear_case: MemoSection
    catalysts: MemoSection
    risks: MemoSection
    conclusion: MemoSection

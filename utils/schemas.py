from __future__ import annotations

from pydantic import BaseModel, Field

class ResearchRequest(BaseModel):
    ticker: str = Field(..., description="Ticker symbol to research")
    analyst_feedback: dict[str, str] = Field(default_factory=dict)


class ResearchResponse(BaseModel):
    ticker: str
    company_name: str
    region: str
    signal_output: dict
    fundamental_output: dict
    context_output: dict
    macro_output: dict
    valuation_output: dict
    risk_output: dict
    memo_output: dict
    critic_output: dict
    evaluator_output: dict
    final_output: dict
    citations: list[dict]
    status_log: list[str]

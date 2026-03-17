from __future__ import annotations

from fastapi import FastAPI

from config.settings import get_settings
from pipelines.research_graph import run_research
from schemas.research_state import ResearchState
from utils.schemas import ResearchRequest, ResearchResponse


app = FastAPI(title="AlphaAgent API", version="0.1.0")
settings = get_settings()


def _payload(state: ResearchState) -> dict:
    return {
        "ticker": state["company_profile"]["ticker"],
        "company_name": state["company_profile"]["company_name"],
        "region": state["company_profile"]["region"],
        "signal_output": state["signal_output"].model_dump(),
        "fundamental_output": state["fundamental_output"],
        "context_output": state["context_output"],
        "macro_output": state["macro_output"],
        "valuation_output": state["valuation_output"],
        "risk_output": state["risk_output"],
        "memo_output": state["memo_output"].model_dump(),
        "critic_output": state["critic_output"],
        "evaluator_output": state["evaluator_output"],
        "final_output": state["final_output"],
        "citations": [citation.model_dump() for citation in state["citations"]],
        "status_log": state["status_log"],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "live"}


@app.get("/research/examples")
def research_examples() -> dict[str, list[str]]:
    return {"tickers": ["AAPL", "MSFT", "NVDA", "TSM", "0700.HK", "005930.KS"]}


@app.post("/research/run", response_model=ResearchResponse)
def research_run(request: ResearchRequest) -> ResearchResponse:
    result = run_research(request.ticker, analyst_feedback=request.analyst_feedback)
    return ResearchResponse(**_payload(result))

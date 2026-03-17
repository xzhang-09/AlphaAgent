from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Ensure Streamlit can resolve top-level packages when launched via `streamlit run app/dashboard.py`.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.analysis_panels import (
    render_context_panel,
    render_critique_panel,
    render_evaluation_panel,
    render_fundamental_panel,
    render_macro_panel,
    render_risk_panel,
    render_signals_panel,
    render_valuation_panel,
)
from app.components.data_status import render_data_status, render_source_badges
from app.components.feedback_panel import render_feedback_panel
from app.components.memo_viewer import render_memo_viewer
from app.components.progress import render_progress
from pipelines.opportunity_pipeline import screen_opportunities
from pipelines.research_graph import run_research
from utils.source_summary import (
    citation_source_counts,
    describe_filings_source,
    describe_fundamentals_source,
    describe_transcripts_source,
)
from utils.ticker import is_valid_ticker_format, normalize_ticker, suggest_ticker_correction


st.set_page_config(page_title="AlphaAgent", layout="wide")
st.title("AlphaAgent: Multi-Agent AI Investment Research")
st.caption("Decision-support workflow for buy-side idea discovery, deep research, critique, and memo generation.")


def to_display(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, list):
        return [to_display(item) for item in value]
    if isinstance(value, dict):
        return {key: to_display(item) for key, item in value.items()}
    return value


def opportunity_rows(selected_ticker: str) -> list[dict]:
    rows = []
    tickers = [selected_ticker] if selected_ticker else None
    for item in screen_opportunities(tickers=tickers):
        signals = to_display(item["signals"])
        rows.append(
            {
                "ticker": item["ticker"],
                "company_name": item["company_name"],
                "score": item["score"],
                "why_now": item["why_now"],
                "event_signals": len(signals.get("event_signals", [])),
                "valuation_signals": len(signals.get("valuation_signals", [])),
                "fundamental_signals": len(signals.get("fundamental_signals", [])),
                "market_signals": len(signals.get("market_signals", [])),
            }
        )
    return rows

with st.sidebar:
    st.header("Research Controls")
    raw_ticker = st.text_input("Ticker", value="")
    st.caption("Enter any live ticker supported by Yahoo Finance, e.g. AAPL, MSFT, 0700.HK, 005930.KS")
    selected_ticker = normalize_ticker(raw_ticker)
    suggested_ticker = suggest_ticker_correction(selected_ticker)
    effective_ticker = suggested_ticker or selected_ticker
    if raw_ticker and suggested_ticker:
        st.warning(f"Using `{effective_ticker}` instead of `{selected_ticker}`.")
    elif raw_ticker and not is_valid_ticker_format(selected_ticker):
        st.error("Ticker format looks invalid. Use symbols like AAPL, 0700.HK, 005930.KS, or JPY=X.")
    feedback = render_feedback_panel()
    run_clicked = st.button("Run Research", type="primary")
    rerun_clicked = st.button("Regenerate Memo With Feedback")


def display_state(result: dict, selected_ticker: str) -> None:
    st.subheader("Pipeline Status")
    render_progress(result["status_log"])

    st.subheader("Data Availability")
    render_data_status(result)

    st.subheader("Opportunity Screen")
    st.dataframe(pd.DataFrame(opportunity_rows(selected_ticker)), use_container_width=True)

    tabs = st.tabs(
        ["Signals", "Fundamentals", "Context", "Macro", "Valuation", "Risk", "Memo", "Critique", "Evaluation"]
    )
    with tabs[0]:
        render_source_badges(["Yahoo Finance market data", describe_fundamentals_source(result["fundamentals_snapshot"])])
        render_signals_panel(result, to_display)
    with tabs[1]:
        render_source_badges(
            [
                describe_fundamentals_source(result["fundamentals_snapshot"]),
                describe_transcripts_source(result["rag_context"].get("transcript_docs", [])),
                describe_filings_source(result["rag_context"].get("filing_docs", [])),
            ]
        )
        render_fundamental_panel(result, to_display)
    with tabs[2]:
        render_source_badges([f"{len(result.get('peer_snapshot', []))} live peers"])
        render_context_panel(result, to_display)
    with tabs[3]:
        render_source_badges([f"{len(result['fx_snapshot'].get('reference_pairs', {}))} live FX pairs"])
        render_macro_panel(result, to_display)
    with tabs[4]:
        render_source_badges(["Valuation model", "Live market snapshot", "Live fundamentals snapshot"])
        render_valuation_panel(result, to_display)
    with tabs[5]:
        render_source_badges(["Live market data", "Peer context", "LLM-free structured risk rules"])
        render_risk_panel(result, to_display)
    with tabs[6]:
        render_source_badges(["Gemini memo synthesis", f"{len(result.get('citations', []))} citations"])
        render_memo_viewer(result)
    with tabs[7]:
        render_source_badges(["Gemini critic", f"{len(result.get('critique_notes', {}).get('issues', []))} issues flagged"])
        render_critique_panel(result, to_display)
    with tabs[8]:
        counts = citation_source_counts(result.get("citations", []))
        render_source_badges(
            ["Evaluator checks"] + [f"{source}={count}" for source, count in sorted(counts.items())]
        )
        render_evaluation_panel(result, to_display)
        st.caption(f"Idea log saved to: {result['final_output'].get('idea_log_path', '')}")


if "result" not in st.session_state:
    st.session_state["result"] = None
if "run_error" not in st.session_state:
    st.session_state["run_error"] = None

if run_clicked and is_valid_ticker_format(effective_ticker):
    try:
        st.session_state["result"] = run_research(effective_ticker)
        st.session_state["run_error"] = None
    except Exception as exc:
        st.session_state["result"] = None
        st.session_state["run_error"] = str(exc)

if rerun_clicked and is_valid_ticker_format(effective_ticker):
    try:
        st.session_state["result"] = run_research(
            effective_ticker,
            analyst_feedback=feedback,
        )
        st.session_state["run_error"] = None
    except Exception as exc:
        st.session_state["result"] = None
        st.session_state["run_error"] = str(exc)

if st.session_state["result"]:
    display_state(st.session_state["result"], effective_ticker)
else:
    if st.session_state["run_error"]:
        st.error(st.session_state["run_error"])
    st.info("Enter any live ticker and run the workflow to analyze it with real external data where available.")

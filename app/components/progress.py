from __future__ import annotations

import streamlit as st


EXPECTED_STEPS = [
    "load_data",
    "signal_agent",
    "fundamental_agent",
    "context_agent",
    "macro_agent",
    "valuation_agent",
    "risk_agent",
    "memo_agent",
    "critic_agent",
    "evaluator",
    "finalize",
]


def render_progress(status_log: list[str]) -> None:
    completed = sum(1 for step in EXPECTED_STEPS if any(log.startswith(step) for log in status_log))
    st.progress(min(completed / len(EXPECTED_STEPS), 1.0), text="Research workflow progress")
    for idx, item in enumerate(status_log, start=1):
        st.write(f"{idx}. {item}")

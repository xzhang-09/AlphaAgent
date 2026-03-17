from __future__ import annotations

import streamlit as st


def render_feedback_panel() -> dict[str, str]:
    return {
        "bull_case": st.text_area("Bull case feedback", placeholder="Refine upside framing..."),
        "bear_case": st.text_area("Bear case feedback", placeholder="Add missing downside risks..."),
        "catalysts": st.text_area("Catalysts feedback", placeholder="Tighten near-term catalysts..."),
        "notes": st.text_area("Analyst notes", placeholder="Optional notebook-style comments..."),
    }

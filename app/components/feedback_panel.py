from __future__ import annotations

import streamlit as st


def render_feedback_panel() -> dict[str, str]:
    return {
        "bull_case": st.text_area(
            "Bull case feedback",
            key="_feedback_bull_case",
            placeholder="Refine upside framing...",
        ),
        "bear_case": st.text_area(
            "Bear case feedback",
            key="_feedback_bear_case",
            placeholder="Add missing downside risks...",
        ),
        "catalysts": st.text_area(
            "Catalysts feedback",
            key="_feedback_catalysts",
            placeholder="Tighten near-term catalysts...",
        ),
        "notes": st.text_area(
            "Analyst notes",
            key="_feedback_notes",
            placeholder="Optional notebook-style comments...",
        ),
    }

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.source_summary import build_data_status, citation_source_counts


def render_data_status(result: dict) -> None:
    statuses = build_data_status(result)
    counts = citation_source_counts(result.get("citations", []))
    primary_docs = len(result.get("rag_context", {}).get("filing_docs", [])) + len(
        result.get("rag_context", {}).get("transcript_docs", [])
    )
    news_docs = len(result.get("rag_context", {}).get("news_docs", [])) + len(
        result.get("rag_context", {}).get("asia_news_docs", [])
    )

    columns = st.columns(4)
    columns[0].metric("Stored Citations", len(result.get("citations", [])))
    columns[1].metric("Filings", len(result.get("rag_context", {}).get("filing_docs", [])))
    columns[2].metric("Transcripts", len(result.get("rag_context", {}).get("transcript_docs", [])))
    columns[3].metric("News Docs", len(result.get("rag_context", {}).get("news_docs", [])))

    st.caption(
        f"Evidence mix: primary_docs={primary_docs}, news_docs={news_docs}. Citation mix: "
        + (
            ", ".join(f"{source}={count}" for source, count in sorted(counts.items()))
            if counts
            else "no citations captured"
        )
    )
    st.dataframe(pd.DataFrame(statuses), use_container_width=True, hide_index=True)


def render_source_badges(labels: list[str]) -> None:
    if not labels:
        st.caption("Sources: unavailable")
        return
    st.caption("Sources: " + " | ".join(labels))

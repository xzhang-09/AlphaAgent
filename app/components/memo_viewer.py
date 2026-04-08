from __future__ import annotations

import streamlit as st

from exports.pdf_export import export_memo_to_pdf_bytes


def render_memo_viewer(result: dict) -> None:
    memo_markdown = result["final_output"]["final_memo_markdown"]
    st.markdown(memo_markdown)
    pdf_bytes = export_memo_to_pdf_bytes(result["final_output"]["title"], memo_markdown)
    st.download_button(
        "Export Memo to PDF",
        data=pdf_bytes,
        file_name=f"{result['company_profile']['ticker']}_memo.pdf",
        mime="application/pdf",
    )

from __future__ import annotations

import pandas as pd
import streamlit as st


def _format_percent_metric(value, unavailable: bool = False) -> str:
    if unavailable or value is None:
        return "N/A"
    return f"{float(value):.1f}%"


def _render_bullets(items: list[str]) -> None:
    if not items:
        st.caption("No items available.")
        return
    for item in items:
        st.markdown(f"- {item}")


def _render_signal_group(title: str, items: list[dict]) -> None:
    st.markdown(f"**{title}**")
    if not items:
        st.caption("No signals triggered.")
        return
    for item in items:
        strength = item.get("strength", 0)
        st.markdown(f"- {item.get('description', '')} `strength {strength:.1f}`")


def render_signals_panel(result: dict, to_display) -> None:
    signals = to_display(result["signals"])
    col1, col2, col3 = st.columns(3)
    col1.metric("Composite Score", f"{signals.get('composite_score', 0):.0f}")
    col2.metric("Candidate", "Yes" if signals.get("candidate") else "No")
    ranked = signals.get("ranked_candidates", [])
    col3.metric("Ranked Ideas", len(ranked))

    st.markdown("**Why Now**")
    st.write(signals.get("why_now", ""))

    left, right = st.columns(2)
    with left:
        _render_signal_group("Event Signals", signals.get("event_signals", []))
        _render_signal_group("Fundamental Signals", signals.get("fundamental_signals", []))
    with right:
        _render_signal_group("Valuation Signals", signals.get("valuation_signals", []))
        _render_signal_group("Market Signals", signals.get("market_signals", []))

    with st.expander("Raw Signal JSON"):
        st.json(signals)


def render_fundamental_panel(result: dict, to_display) -> None:
    fundamentals = to_display(result["fundamental_summary"])
    snapshot = to_display(result.get("fundamentals_snapshot", {}))
    quality_flags = set(snapshot.get("data_quality_flags", []))
    trends = fundamentals.get("revenue_margin_trends", {})
    cash_flow = fundamentals.get("cash_flow_quality", {})

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Revenue Growth",
        _format_percent_metric(
            trends.get("revenue_growth_yoy"),
            "revenue_growth_unavailable" in quality_flags,
        ),
    )
    col2.metric(
        "Gross Margin",
        _format_percent_metric(
            trends.get("gross_margin"),
            "gross_margin_unavailable" in quality_flags,
        ),
    )
    col3.metric(
        "EBIT Margin",
        _format_percent_metric(
            trends.get("ebit_margin"),
            "ebit_margin_unavailable" in quality_flags,
        ),
    )

    st.markdown("**Business Overview**")
    st.write(fundamentals.get("business_overview", ""))

    st.markdown("**Revenue and Margin Trend**")
    st.write(trends.get("summary", ""))

    st.markdown("**Cash Flow Quality**")
    st.write(cash_flow.get("commentary", ""))
    sub1, sub2 = st.columns(2)
    sub1.metric(
        "FCF Margin",
        _format_percent_metric(
            cash_flow.get("fcf_margin"),
            "fcf_margin_unavailable" in quality_flags,
        ),
    )
    sub2.metric(
        "Cash Conversion",
        _format_percent_metric(
            cash_flow.get("cash_conversion"),
            "cash_conversion_unavailable" in quality_flags,
        ),
    )

    st.markdown("**Key Business Drivers**")
    _render_bullets(fundamentals.get("key_business_drivers", []))

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("**Management Commentary**")
        _render_bullets(fundamentals.get("management_commentary", []))
    with col_right:
        st.markdown("**Filing Support**")
        _render_bullets(fundamentals.get("filing_support", []))

    with st.expander("Raw Fundamental JSON"):
        st.json(fundamentals)


def render_context_panel(result: dict, to_display) -> None:
    context = to_display(result["context_summary"])
    st.markdown("**Sector Trend Summary**")
    st.write(context.get("sector_trend_summary", ""))

    st.markdown("**Peer Takeaway**")
    st.write(context.get("peer_takeaway", ""))

    peers = context.get("peer_comparison", [])
    st.markdown("**Peer Comparison**")
    if peers:
        st.dataframe(pd.DataFrame(peers), use_container_width=True, hide_index=True)
    else:
        st.caption("No peer data available for this run.")

    with st.expander("Raw Context JSON"):
        st.json(context)


def render_macro_panel(result: dict, to_display) -> None:
    macro = to_display(result["macro_summary"])
    st.markdown("**Sector Backdrop**")
    st.write(macro.get("sector_backdrop", ""))

    st.markdown("**Rates Context**")
    st.write(macro.get("rates_context", ""))

    st.markdown("**FX Context**")
    st.write(macro.get("fx_context", ""))

    cols = st.columns(2)
    with cols[0]:
        st.markdown("**Regional Context**")
        st.write(macro.get("regional_context", ""))
    with cols[1]:
        st.markdown("**Currency Sensitivity**")
        st.write(macro.get("currency_sensitivity", ""))

    st.markdown("**Reference Pairs**")
    _render_bullets(macro.get("reference_pairs", []))

    with st.expander("Raw Macro JSON"):
        st.json(macro)


def render_valuation_panel(result: dict, to_display) -> None:
    valuation = to_display(result["valuation_summary"])
    relative = valuation.get("relative_valuation", {})
    scenarios = valuation.get("scenario_analysis", {})

    top = st.columns(4)
    top[0].metric("Current Price", f"{valuation.get('current_price', 0):.2f}")
    top[1].metric("Forward P/E", f"{relative.get('forward_pe', 0):.1f}x")
    top[2].metric("Peer P/E", f"{relative.get('peer_forward_pe', 0):.1f}x")
    top[3].metric("Hist. Percentile", f"{valuation.get('historical_percentile', 0):.0f}")

    st.markdown("**Scenario Analysis**")
    if scenarios:
        rows = []
        for name, values in scenarios.items():
            rows.append(
                {
                    "scenario": name,
                    "target_price": values.get("target_price"),
                    "upside_pct": values.get("upside_pct"),
                    "revenue_growth_pct": values.get("revenue_growth_pct"),
                    "ebit_margin_pct": values.get("ebit_margin_pct"),
                    "target_pe": values.get("target_pe"),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        base = scenarios.get("base", {})
        if base.get("thesis"):
            st.markdown("**Base Case Framing**")
            st.write(base.get("thesis"))

    st.markdown("**Sensitivity Table**")
    st.dataframe(pd.DataFrame(result["valuation_output"]["sensitivity_table"]), use_container_width=True, hide_index=True)

    with st.expander("Raw Valuation JSON"):
        st.json(valuation)


def render_risk_panel(result: dict, to_display) -> None:
    risk = to_display(result["risk_summary"])
    st.markdown("**Bear Case Summary**")
    _render_bullets(
        [
            f"Competition: {risk.get('competition', '')}",
            f"Regulation: {risk.get('regulation', '')}",
            f"Macro: {risk.get('macro_risk', '')}",
            f"Execution: {risk.get('execution_risk', '')}",
            f"Valuation Compression: {risk.get('valuation_compression', '')}",
        ]
    )

    st.markdown("**Factor / Style Exposure**")
    factor_exposure = risk.get("factor_style_exposure", {})
    if factor_exposure:
        st.dataframe(
            pd.DataFrame(
                [{"factor": factor, "exposure": exposure} for factor, exposure in factor_exposure.items()]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No factor/style exposure data available.")

    with st.expander("Raw Risk JSON"):
        st.json(risk)


def render_critique_panel(result: dict, to_display) -> None:
    critique = to_display(result["critique_notes"])
    issues = critique.get("issues", [])

    top = st.columns(3)
    top[0].metric("Issues Flagged", len(issues))
    top[1].metric("Needs Refinement", "Yes" if critique.get("needs_refinement") else "No")
    top[2].metric("Target", critique.get("refinement_target") or "None")

    st.markdown("**Critic Findings**")
    if issues:
        st.dataframe(pd.DataFrame(issues), use_container_width=True, hide_index=True)
    else:
        st.caption("No critique issues flagged in this run.")

    with st.expander("Raw Critique JSON"):
        st.json(critique)


def render_evaluation_panel(result: dict, to_display) -> None:
    evaluation = to_display(result["evaluator_output"])
    top = st.columns(3)
    top[0].metric("Passed", "Yes" if evaluation.get("passed") else "No")
    top[1].metric("Numerical Mismatches", len(evaluation.get("numerical_mismatches", [])))
    top[2].metric("Hallucination Flags", len(evaluation.get("hallucination_flags", [])))

    left, right = st.columns(2)
    with left:
        st.markdown("**Numerical Checks**")
        _render_bullets(evaluation.get("numerical_mismatches", []))
    with right:
        st.markdown("**Reasoning / Hallucination Flags**")
        _render_bullets(evaluation.get("hallucination_flags", []))

    st.markdown("**Citation Metadata**")
    citations = evaluation.get("citation_metadata", [])
    if citations:
        st.dataframe(pd.DataFrame(citations), use_container_width=True, hide_index=True)
    else:
        st.caption("No citations were stored for this run.")

    with st.expander("Raw Evaluation JSON"):
        st.json(evaluation)

from __future__ import annotations

from collections import Counter


def citation_source_counts(citations: list) -> dict[str, int]:
    normalized = []
    for citation in citations:
        if hasattr(citation, "source_type"):
            normalized.append(citation.source_type)
        elif isinstance(citation, dict):
            normalized.append(citation.get("source_type", "unknown"))
    return dict(Counter(normalized))


def _display_source_name(source: str) -> str:
    mapping = {
        "financial_modeling_prep": "FMP Stable",
        "yahoo_finance_fallback": "Yahoo Fallback",
        "yahoo_finance": "Yahoo Finance",
        "sec_fallback": "SEC Fallback",
    }
    return mapping.get(source, source.replace("_", " ").title())


def describe_fundamentals_source(snapshot: dict) -> str:
    return _display_source_name(snapshot.get("source", "live_data"))


def describe_filings_source(docs: list[dict]) -> str:
    if not docs:
        return "SEC / FMP"
    if any(str(doc.get("source", "")) == "sec_fallback" for doc in docs):
        return "SEC Fallback"
    if any(str(doc.get("source", "")) == "fmp_stable" for doc in docs):
        return "FMP Stable"
    if any("sec.gov" in str(doc.get("url", "")) for doc in docs):
        return "SEC Fallback"
    return "FMP Stable"


def describe_transcripts_source(docs: list[dict]) -> str:
    if docs:
        return "FMP Stable"
    return "Transcript API / FMP"


def build_data_status(result: dict) -> list[dict[str, str]]:
    rag_context = result.get("rag_context", {})
    fundamentals_snapshot = result.get("fundamentals_snapshot", {})
    statuses = [
        {
            "section": "Market Data",
            "status": "available" if result.get("market_snapshot", {}).get("current_price") else "missing",
            "source": "Yahoo Finance",
            "detail": f"Price {result.get('market_snapshot', {}).get('current_price', 'n/a')}",
        },
        {
            "section": "Fundamentals",
            "status": "available" if fundamentals_snapshot else "missing",
            "source": describe_fundamentals_source(fundamentals_snapshot),
            "detail": (
                fundamentals_snapshot.get("source_detail")
                or fundamentals_snapshot.get("source_warning")
                or f"Revenue growth {fundamentals_snapshot.get('revenue_growth_yoy', 'n/a')}"
            ),
        },
        {
            "section": "Filings",
            "status": "available" if rag_context.get("filing_docs") else "missing",
            "source": describe_filings_source(rag_context.get("filing_docs", [])),
            "detail": (
                f"{len(rag_context.get('filing_docs', []))} docs"
                if rag_context.get("filing_docs")
                else "No FMP or SEC filing excerpt was retrieved for this run."
            ),
        },
        {
            "section": "Transcripts",
            "status": "available" if rag_context.get("transcript_docs") else "missing",
            "source": describe_transcripts_source(rag_context.get("transcript_docs", [])),
            "detail": f"{len(rag_context.get('transcript_docs', []))} docs",
        },
        {
            "section": "News",
            "status": "available" if rag_context.get("news_docs") else "missing",
            "source": "News API / Google News",
            "detail": f"{len(rag_context.get('news_docs', []))} docs",
        },
        {
            "section": "Asia News",
            "status": "available" if rag_context.get("asia_news_docs") else "missing",
            "source": "Regional news search",
            "detail": f"{len(rag_context.get('asia_news_docs', []))} docs",
        },
        {
            "section": "FX",
            "status": "available" if result.get("fx_snapshot", {}).get("reference_pairs") else "missing",
            "source": "Yahoo Finance FX",
            "detail": f"{len(result.get('fx_snapshot', {}).get('reference_pairs', {}))} live pairs",
        },
        {
            "section": "Peers",
            "status": "available" if result.get("peer_snapshot") else "missing",
            "source": "Curated peer map + live quotes",
            "detail": f"{len(result.get('peer_snapshot', []))} peers",
        },
    ]
    return statuses

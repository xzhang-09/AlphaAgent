from __future__ import annotations

from schemas.signals import Citation


def build_citations(rag_context: dict) -> list[dict]:
    citations: list[Citation] = []
    seen_ids: set[str] = set()
    for doc_group, source_type in (
        ("filing_docs", "filing"),
        ("transcript_docs", "transcript"),
        ("news_docs", "news"),
        ("asia_news_docs", "asia_news"),
    ):
        for document in rag_context.get(doc_group, []):
            if document["id"] in seen_ids:
                continue
            seen_ids.add(document["id"])
            citations.append(
                Citation(
                    citation_id=document["id"],
                    source_type=source_type,
                    title=document["title"],
                    snippet=document["snippet"],
                )
            )
    return citations

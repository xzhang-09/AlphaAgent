from __future__ import annotations

from data.asia_news_loader import AsiaNewsLoader
from data.filings_loader import FilingsLoader
from data.news_loader import NewsLoader
from data.transcripts_loader import TranscriptsLoader
from data.vector_store import SimpleVectorStore


class RAGProcessor:
    def __init__(self) -> None:
        self.filings_loader = FilingsLoader()
        self.transcripts_loader = TranscriptsLoader()
        self.news_loader = NewsLoader()
        self.asia_news_loader = AsiaNewsLoader()

    def build_context(self, ticker: str) -> dict:
        filing_docs = self.filings_loader.load(ticker)
        transcript_docs = self.transcripts_loader.load(ticker)
        news_docs = self.news_loader.load(ticker)
        asia_news_docs = self.asia_news_loader.load(ticker)

        store = SimpleVectorStore(namespace=ticker.lower())
        store.add_documents(filing_docs + transcript_docs + news_docs + asia_news_docs)

        return {
            "vector_store": store,
            "filing_docs": filing_docs,
            "transcript_docs": transcript_docs,
            "news_docs": news_docs,
            "asia_news_docs": asia_news_docs,
        }

    def retrieve(self, context: dict, query: str, top_k: int = 3) -> list[dict]:
        results = context["vector_store"].search(query, top_k=top_k)
        return [
            {
                **item,
                "metadata": {
                    "citation_id": item.get("id"),
                    "title": item.get("title"),
                },
            }
            for item in results
        ]

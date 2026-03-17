from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from config.settings import get_settings


class SimpleVectorStore:
    """A tiny lexical vector store that handles English and basic Chinese text."""

    def __init__(self, namespace: str = "default") -> None:
        settings = get_settings()
        self.path = Path(settings.vector_db_path) / f"{namespace}.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.documents: list[dict] = []
        if self.path.exists():
            self.documents = json.loads(self.path.read_text())

    def add_documents(self, docs: list[dict]) -> None:
        existing_ids = {doc.get("id") for doc in self.documents}
        for doc in docs:
            if doc.get("id") in existing_ids:
                continue
            self.documents.append(doc)
            existing_ids.add(doc.get("id"))
        self.persist()

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        query_tokens = self._tokenize(query)
        scored_docs = []
        for doc in self.documents:
            doc_tokens = self._tokenize(f"{doc.get('title', '')} {doc.get('snippet', '')}")
            overlap = sum((Counter(doc_tokens) & Counter(query_tokens)).values())
            scored_docs.append((overlap, doc))
        scored_docs.sort(key=lambda item: item[0], reverse=True)
        return [doc for score, doc in scored_docs[:top_k] if score > 0] or self.documents[:top_k]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        english_tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
        chinese_tokens = re.findall(r"[\u4e00-\u9fff]", text)
        return english_tokens + chinese_tokens

    def persist(self) -> None:
        self.path.write_text(json.dumps(self.documents, ensure_ascii=False, indent=2))

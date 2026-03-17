from __future__ import annotations

from data.clients import TranscriptClient


class TranscriptsLoader:
    def __init__(self) -> None:
        self.client = TranscriptClient()

    def load(self, ticker: str) -> list[dict]:
        try:
            return self.client.get_transcripts(ticker)
        except Exception:
            return []

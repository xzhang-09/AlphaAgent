from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from config.settings import get_settings
from schemas.base import DictLikeModel


def _serialize(value):
    if isinstance(value, DictLikeModel):
        return value.model_dump()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


class IdeaLogStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        settings = get_settings()
        self.base_dir = base_dir or settings.ideas_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_run(self, state) -> Path:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = self.base_dir / f"{timestamp}_{state['ticker']}.json"
        payload = {
            "timestamp": timestamp,
            "ticker": state["ticker"],
            "signal_summary": _serialize(state["signal_output"]),
            "memo_draft": _serialize(state["memo_output"]),
            "critique_notes": _serialize(state["critic_output"]),
            "analyst_feedback": _serialize(state["analyst_feedback"]),
            "final_memo": _serialize(state["final_output"]),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        return path

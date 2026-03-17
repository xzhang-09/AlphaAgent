from __future__ import annotations

import json
import re

from config.settings import get_settings
from data.clients import BaseAPIClient


class LLMClient(BaseAPIClient):
    """Gemini wrapper using Google's OpenAI-compatible endpoint."""

    def __init__(self, model: str | None = None) -> None:
        settings = get_settings()
        super().__init__(api_key_env="GEMINI_API_KEY", base_url_env="GEMINI_BASE_URL")
        self.model = model or settings.gemini_model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, fallback: str) -> str:
        if not self.is_configured():
            return fallback

        def _request() -> str:
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                default_headers={"x-goog-api-client": "alpha-agent/0.1.0"},
            )
            response = client.responses.create(model=self.model, input=prompt)
            return response.output_text

        try:
            return self.with_retry("llm_generate", _request)
        except Exception:
            return fallback

    def generate_json(self, prompt: str, fallback: dict | list) -> dict | list:
        fallback_text = json.dumps(fallback, ensure_ascii=False)
        raw = self.generate(
            prompt=(
                f"{prompt}\n\n"
                "Return valid JSON only. Do not wrap the JSON in markdown fences."
            ),
            fallback=fallback_text,
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"(\{.*\}|\[.*\])", raw, flags=re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
        return fallback

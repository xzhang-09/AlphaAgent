from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class DictLikeModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True, extra="allow")

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def update(self, values: dict[str, Any]) -> None:
        for key, value in values.items():
            setattr(self, key, value)

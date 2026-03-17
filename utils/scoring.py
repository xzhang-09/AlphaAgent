from __future__ import annotations


def bounded_score(parts: list[float]) -> float:
    return max(0.0, min(100.0, sum(parts)))

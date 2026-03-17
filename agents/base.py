from __future__ import annotations

from abc import ABC, abstractmethod

from schemas.research_state import ResearchState


class BaseAgent(ABC):
    """Shared interface for all research agents."""

    name: str = "base_agent"
    output_key: str = "agent_output"
    state_alias_key: str | None = None

    def run(self, state: ResearchState) -> ResearchState:
        output = self.analyze(state)
        state[self.output_key] = output
        if self.state_alias_key:
            state[self.state_alias_key] = output
        return state

    @abstractmethod
    def analyze(self, state: ResearchState) -> dict:
        raise NotImplementedError

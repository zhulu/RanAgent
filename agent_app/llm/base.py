from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agent_app.core.messages import Message


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str


@dataclass(slots=True)
class LLMDecision:
    action: str
    content: str | None = None
    tool_name: str | None = None
    tool_input: str | None = None


class LLMBackend(Protocol):
    def decide(self, messages: list[Message], tools: list[ToolSpec]) -> LLMDecision:
        """Return either a direct response or a tool call decision."""

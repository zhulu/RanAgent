from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class ToolResult:
    content: str


class Tool(Protocol):
    name: str
    description: str

    def run(self, tool_input: str) -> ToolResult:
        """Execute the tool and return a structured result."""

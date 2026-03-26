from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class ToolResult:
    content: str


class Tool(Protocol):
    name: str
    description: str
    input_schema: dict[str, Any]
    example_input: str

    def run(self, tool_input: str) -> ToolResult:
        """Execute the tool and return a structured result."""

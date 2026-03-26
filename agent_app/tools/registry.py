from __future__ import annotations

from collections.abc import Iterable

from agent_app.llm.base import ToolSpec
from agent_app.tools.base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return sorted(self._tools)

    def specs(self, allowed_names: Iterable[str] | None = None) -> list[ToolSpec]:
        allowed = set(allowed_names) if allowed_names is not None else None
        return [
            ToolSpec(
                name=tool.name,
                description=tool.description,
                input_schema=getattr(tool, "input_schema", None),
                example_input=getattr(tool, "example_input", None),
            )
            for tool in self._tools.values()
            if allowed is None or tool.name in allowed
        ]

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Skill:
    name: str
    description: str
    prompt: str
    allowed_tools: tuple[str, ...]
    source_path: Path

    def to_system_prompt(self) -> str:
        lines = [
            f"Skill Name: {self.name}",
            f"Skill Description: {self.description or 'No description provided.'}",
        ]
        if self.allowed_tools:
            lines.append(f"Skill Tools: {', '.join(self.allowed_tools)}")
        lines.append("Skill Prompt:")
        lines.append(self.prompt.strip() or "No additional prompt provided.")
        return "\n".join(lines)

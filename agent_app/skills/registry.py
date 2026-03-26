from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agent_app.skills.base import Skill
from agent_app.skills.loader import load_skill_from_markdown


@dataclass(slots=True)
class SkillRegistry:
    skills: list[Skill]
    _by_name: dict[str, Skill] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._by_name = {skill.name: skill for skill in self.skills}

    @classmethod
    def from_directory(cls, skill_dir: Path) -> "SkillRegistry":
        if not skill_dir.exists():
            return cls([])

        skills = [
            load_skill_from_markdown(path)
            for path in sorted(skill_dir.glob("*.md"))
            if path.is_file()
        ]
        return cls(skills)

    def list_skills(self) -> list[Skill]:
        return list(self.skills)

    def resolve(self, names: list[str]) -> list[Skill]:
        resolved: list[Skill] = []
        for name in names:
            if name not in self._by_name:
                available = ", ".join(sorted(self._by_name)) or "none"
                raise KeyError(f"Skill not found: {name}. Available skills: {available}")
            resolved.append(self._by_name[name])
        return resolved

    def allowed_tools_for(self, names: list[str]) -> set[str] | None:
        resolved = self.resolve(names)
        allowed_groups = [set(skill.allowed_tools) for skill in resolved if skill.allowed_tools]
        if not allowed_groups:
            return None

        allowed: set[str] = set()
        for group in allowed_groups:
            allowed.update(group)
        return allowed

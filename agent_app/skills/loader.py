from __future__ import annotations

from pathlib import Path

from agent_app.skills.base import Skill


def load_skill_from_markdown(path: Path) -> Skill:
    raw_text = path.read_text(encoding="utf-8")
    metadata, body = _parse_markdown_skill(raw_text)
    name = metadata.get("name", path.stem)
    description = metadata.get("description", "")
    allowed_tools = tuple(
        tool.strip()
        for tool in metadata.get("tools", "").split(",")
        if tool.strip()
    )
    return Skill(
        name=name,
        description=description,
        prompt=body.strip(),
        allowed_tools=allowed_tools,
        source_path=path,
    )


def _parse_markdown_skill(raw_text: str) -> tuple[dict[str, str], str]:
    text = raw_text.lstrip("\ufeff")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    metadata: dict[str, str] = {}
    body_start = 0
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            body_start = index + 1
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip().lower()] = value.strip()
    else:
        return {}, text

    body = "\n".join(lines[body_start:])
    return metadata, body

from __future__ import annotations

from dataclasses import dataclass, field

from agent_app.core.messages import Message


@dataclass(slots=True)
class SessionState:
    session_id: str
    messages: list[Message] = field(default_factory=list)

    def add(self, role: str, content: str, name: str | None = None) -> Message:
        message = Message(role=role, content=content, name=name)
        self.messages.append(message)
        return message

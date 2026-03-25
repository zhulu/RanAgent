from __future__ import annotations

import json
from pathlib import Path

from agent_app.core.messages import Message
from agent_app.core.state import SessionState


class JsonSessionStore:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def load(self, session_id: str) -> SessionState:
        path = self._path_for(session_id)
        if not path.exists():
            return SessionState(session_id=session_id)

        payload = json.loads(path.read_text(encoding="utf-8"))
        return SessionState(
            session_id=payload["session_id"],
            messages=[Message.from_dict(item) for item in payload["messages"]],
        )

    def save(self, state: SessionState) -> None:
        payload = {
            "session_id": state.session_id,
            "messages": [message.to_dict() for message in state.messages],
        }
        self._path_for(state.session_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _path_for(self, session_id: str) -> Path:
        safe_session_id = session_id.replace("/", "_").replace("\\", "_")
        return self._base_dir / f"{safe_session_id}.json"

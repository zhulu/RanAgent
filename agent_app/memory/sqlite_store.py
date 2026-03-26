from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from agent_app.core.messages import Message


@dataclass(frozen=True, slots=True)
class MemoryHit:
    session_id: str
    role: str
    content: str
    score: int
    created_at: str


class SqliteMemoryStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def add_messages(self, session_id: str, messages: list[Message]) -> None:
        if not messages:
            return

        with closing(self._connect()) as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT INTO memory_entries (session_id, role, content)
                    VALUES (?, ?, ?)
                    """,
                    [(session_id, message.role, message.content) for message in messages],
                )

    def search(self, query: str, limit: int = 5) -> list[MemoryHit]:
        tokens = self._tokenize(query)
        if not tokens:
            return []

        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT session_id, role, content, created_at
                FROM memory_entries
                ORDER BY id DESC
                LIMIT 500
                """
            ).fetchall()

        hits: list[MemoryHit] = []
        for session_id, role, content, created_at in rows:
            haystack = content.lower()
            score = sum(1 for token in tokens if token in haystack)
            if score > 0:
                hits.append(
                    MemoryHit(
                        session_id=session_id,
                        role=role,
                        content=content,
                        score=score,
                        created_at=created_at,
                    )
                )

        hits.sort(key=lambda item: (-item.score, item.created_at))
        return hits[:limit]

    def format_context(self, query: str, limit: int = 3) -> str | None:
        hits = self.search(query, limit=limit)
        if not hits:
            return None

        lines = ["Relevant memory:"]
        for hit in hits:
            snippet = hit.content.strip().replace("\n", " ")
            if len(snippet) > 180:
                snippet = snippet[:177] + "..."
            lines.append(f"- [{hit.session_id}/{hit.role}] {snippet}")
        return "\n".join(lines)

    def delete_session(self, session_id: str) -> int:
        with closing(self._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    DELETE FROM memory_entries
                    WHERE session_id = ?
                    """,
                    (session_id,),
                )
                return int(cursor.rowcount)

    def list_sessions(self, limit: int = 50) -> list[str]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT session_id
                FROM memory_entries
                ORDER BY session_id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [row[0] for row in rows]

    def _init_schema(self) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memory_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_memory_entries_session
                    ON memory_entries(session_id)
                    """
                )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        tokens = [token.lower() for token in re.findall(r"[\w\u4e00-\u9fff]+", text)]
        tokens = [token for token in tokens if len(token) >= 2]
        if not tokens and text.strip():
            return [text.strip().lower()]
        return tokens

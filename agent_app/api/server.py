from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent_app.config import Settings, get_settings
from agent_app.main import build_agent, build_memory_store, build_skill_registry, build_tool_registry
from agent_app.memory.session_store import JsonSessionStore


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str = "default"
    skills: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="RanAgent", version="0.1.0")

    agent = build_agent(settings)
    skill_registry = build_skill_registry(settings)
    tool_registry = build_tool_registry(settings)
    memory_store = build_memory_store(settings)
    session_store = JsonSessionStore(settings.session_store_dir)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/config")
    def show_config() -> dict[str, object]:
        model_config = settings.resolve_model_config()
        return {
            "model_provider": model_config.provider,
            "model_name": model_config.model_name,
            "base_url": model_config.base_url,
            "workspace_root": str(settings.workspace_root),
            "skills_dir": str(settings.skills_dir),
            "session_store_dir": str(settings.session_store_dir),
            "memory_db_path": str(settings.memory_db_path),
            "max_tool_iterations": settings.max_tool_iterations,
            "max_tool_result_chars": settings.max_tool_result_chars,
            "max_memory_context_hits": settings.max_memory_context_hits,
        }

    @app.get("/tools")
    def list_tools() -> list[dict[str, object]]:
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "input_schema": spec.input_schema,
                "example_input": spec.example_input,
            }
            for spec in tool_registry.specs()
        ]

    @app.get("/skills")
    def list_skills() -> list[dict[str, object]]:
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "allowed_tools": list(skill.allowed_tools),
            }
            for skill in skill_registry.list_skills()
        ]

    @app.get("/sessions")
    def list_sessions() -> dict[str, list[str]]:
        session_ids = sorted(set(session_store.list_session_ids()) | set(memory_store.list_sessions()))
        return {"sessions": session_ids}

    @app.get("/sessions/{session_id}")
    def get_session(session_id: str) -> dict[str, object]:
        state = session_store.load(session_id)
        if not state.messages:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "session_id": session_id,
            "messages": [message.to_dict() for message in state.messages],
        }

    @app.delete("/sessions/{session_id}")
    def delete_session(session_id: str) -> dict[str, object]:
        session_deleted = session_store.delete(session_id)
        memory_deleted = memory_store.delete_session(session_id)
        if not session_deleted and memory_deleted == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "session_id": session_id,
            "session_deleted": session_deleted,
            "memory_deleted": memory_deleted,
        }

    @app.get("/memories/search")
    def search_memories(q: str, limit: int = 5) -> list[dict[str, object]]:
        hits = memory_store.search(q, limit=limit)
        return [
            {
                "session_id": hit.session_id,
                "role": hit.role,
                "content": hit.content,
                "score": hit.score,
                "created_at": hit.created_at,
            }
            for hit in hits
        ]

    @app.delete("/memories/session/{session_id}")
    def delete_session_memories(session_id: str) -> dict[str, object]:
        deleted = memory_store.delete_session(session_id)
        if deleted == 0:
            raise HTTPException(status_code=404, detail="No memory entries for session")
        return {"session_id": session_id, "deleted": deleted}

    @app.post("/chat", response_model=ChatResponse)
    def chat(payload: ChatRequest) -> ChatResponse:
        response = agent.run(
            payload.message,
            session_id=payload.session_id,
            skill_names=payload.skills,
        )
        return ChatResponse(response=response)

    return app


app = create_app()

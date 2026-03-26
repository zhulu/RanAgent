from __future__ import annotations

import argparse

from agent_app.config import Settings, get_settings
from agent_app.core.agent import Agent
from agent_app.llm.factory import build_llm_backend
from agent_app.memory.session_store import JsonSessionStore
from agent_app.memory.sqlite_store import SqliteMemoryStore
from agent_app.skills.registry import SkillRegistry
from agent_app.tools.calculator import CalculatorTool
from agent_app.tools.document_readers import ReadPdfTool, ReadWordTool, ReadXlsxTool
from agent_app.tools.filesystem import (
    ListDirTool,
    MoveFileTool,
    ReadFileTool,
    RemoveFileTool,
    RenameFileTool,
    SearchInFilesTool,
    StatFileTool,
    WriteFileTool,
)
from agent_app.tools.registry import ToolRegistry
from agent_app.tools.time_tool import TimeNowTool


def build_tool_registry(settings: Settings) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(TimeNowTool())
    registry.register(CalculatorTool())
    registry.register(ReadFileTool(settings.workspace_root))
    registry.register(WriteFileTool(settings.workspace_root))
    registry.register(RenameFileTool(settings.workspace_root))
    registry.register(MoveFileTool(settings.workspace_root))
    registry.register(RemoveFileTool(settings.workspace_root))
    registry.register(ListDirTool(settings.workspace_root))
    registry.register(SearchInFilesTool(settings.workspace_root))
    registry.register(StatFileTool(settings.workspace_root))
    registry.register(ReadPdfTool(settings.workspace_root))
    registry.register(ReadXlsxTool(settings.workspace_root))
    registry.register(ReadWordTool(settings.workspace_root))
    return registry


def build_skill_registry(settings: Settings) -> SkillRegistry:
    return SkillRegistry.from_directory(settings.skills_dir)


def build_memory_store(settings: Settings) -> SqliteMemoryStore:
    return SqliteMemoryStore(settings.memory_db_path)


def build_agent(settings: Settings | None = None) -> Agent:
    settings = settings or get_settings()
    llm = build_llm_backend(settings.resolve_model_config())
    session_store = JsonSessionStore(settings.session_store_dir)
    return Agent(
        llm=llm,
        tool_registry=build_tool_registry(settings),
        session_store=session_store,
        skill_registry=build_skill_registry(settings),
        memory_store=build_memory_store(settings),
        max_tool_iterations=settings.max_tool_iterations,
        max_tool_result_chars=settings.max_tool_result_chars,
        max_memory_context_hits=settings.max_memory_context_hits,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal Python agent framework")
    parser.add_argument("message", nargs="?", help="User input to the agent")
    parser.add_argument("--session-id", default="default")
    parser.add_argument("--provider", choices=["mock", "openai", "gemini", "glm", "glm-4.7"])
    parser.add_argument("--model")
    parser.add_argument("--api-key")
    parser.add_argument("--base-url")
    parser.add_argument(
        "--skills",
        help="Comma-separated skill names to load for this run",
    )
    parser.add_argument(
        "--list-skills",
        action="store_true",
        help="List available skills and exit",
    )
    parser.add_argument(
        "--show-model-config",
        action="store_true",
        help="Print resolved model configuration and exit",
    )
    args = parser.parse_args()

    settings = get_settings(
        model_provider=args.provider,
        model_name_override=args.model,
        api_key_override=args.api_key,
        base_url_override=args.base_url,
    )

    if args.show_model_config:
        print(settings.resolve_model_config().to_json())
        return

    skill_registry = build_skill_registry(settings)
    if args.list_skills:
        skills = skill_registry.list_skills()
        if not skills:
            print("No skills found.")
            return
        for skill in skills:
            print(f"{skill.name}: {skill.description}")
        return

    if not args.message:
        parser.error("message is required unless --show-model-config is used")

    skill_names = [name.strip() for name in (args.skills or "").split(",") if name.strip()]
    agent = build_agent(settings)
    print(agent.run(args.message, session_id=args.session_id, skill_names=skill_names))


if __name__ == "__main__":
    main()

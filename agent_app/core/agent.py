from __future__ import annotations

from agent_app.core.messages import Message
from agent_app.core.state import SessionState
from agent_app.llm.base import LLMBackend
from agent_app.memory.session_store import JsonSessionStore
from agent_app.memory.sqlite_store import SqliteMemoryStore
from agent_app.observability.logger import get_logger
from agent_app.skills.base import Skill
from agent_app.skills.registry import SkillRegistry
from agent_app.tools.registry import ToolRegistry


class Agent:
    def __init__(
        self,
        llm: LLMBackend,
        tool_registry: ToolRegistry,
        session_store: JsonSessionStore,
        skill_registry: SkillRegistry | None = None,
        memory_store: SqliteMemoryStore | None = None,
        max_tool_iterations: int = 3,
        max_tool_result_chars: int = 4000,
        max_memory_context_hits: int = 3,
    ) -> None:
        self._llm = llm
        self._tool_registry = tool_registry
        self._session_store = session_store
        self._skill_registry = skill_registry or SkillRegistry([])
        self._memory_store = memory_store
        self._max_tool_iterations = max_tool_iterations
        self._max_tool_result_chars = max_tool_result_chars
        self._max_memory_context_hits = max_memory_context_hits
        self._logger = get_logger(self.__class__.__name__)

    def run(
        self,
        user_input: str,
        session_id: str = "default",
        skill_names: list[str] | None = None,
    ) -> str:
        state = self._session_store.load(session_id)
        new_messages: list[Message] = []
        new_messages.append(state.add(role="user", content=user_input))

        skills = self._skill_registry.resolve(skill_names or [])
        allowed_tools = self._skill_registry.allowed_tools_for(skill_names or [])
        memory_context = (
            self._memory_store.format_context(
                user_input,
                limit=self._max_memory_context_hits,
            )
            if self._memory_store
            else None
        )

        reply = self._run_loop(
            state,
            skills=skills,
            allowed_tools=allowed_tools,
            memory_context=memory_context,
            new_messages=new_messages,
        )
        self._session_store.save(state)
        if self._memory_store:
            self._memory_store.add_messages(session_id, new_messages)
        return reply

    def _run_loop(
        self,
        state: SessionState,
        *,
        skills: list[Skill],
        allowed_tools: set[str] | None,
        memory_context: str | None,
        new_messages: list[Message],
    ) -> str:
        runtime_messages = self._build_runtime_messages(state, skills, memory_context)
        for _ in range(self._max_tool_iterations):
            decision = self._llm.decide(
                messages=runtime_messages,
                tools=self._tool_registry.specs(allowed_tools),
            )
            if decision.action == "respond":
                content = decision.content or "未生成回复。"
                new_messages.append(state.add(role="assistant", content=content))
                return content

            if decision.action != "tool" or not decision.tool_name:
                fallback = "模型返回了无法识别的动作。"
                new_messages.append(state.add(role="assistant", content=fallback))
                return fallback

            if allowed_tools is not None and decision.tool_name not in allowed_tools:
                fallback = (
                    f"工具 {decision.tool_name} 不在当前 skill 允许范围内。"
                    f"允许工具：{', '.join(sorted(allowed_tools))}"
                )
                new_messages.append(state.add(role="assistant", content=fallback))
                return fallback

            tool = self._tool_registry.get(decision.tool_name)
            tool_input = decision.tool_input or ""
            self._logger.info("Running tool %s with input: %s", tool.name, tool_input)
            result = tool.run(tool_input)
            tool_content = self._truncate_text(result.content)
            new_messages.append(state.add(role="tool", content=tool_content, name=tool.name))
            runtime_messages = self._build_runtime_messages(state, skills, memory_context)

        fallback = "已达到最大工具调用次数，请缩小问题范围或调整规划策略。"
        new_messages.append(state.add(role="assistant", content=fallback))
        return fallback

    def _build_runtime_messages(
        self,
        state: SessionState,
        skills: list[Skill],
        memory_context: str | None,
    ) -> list[Message]:
        messages: list[Message] = []
        for skill in skills:
            messages.append(Message(role="system", content=skill.to_system_prompt()))
        if memory_context:
            messages.append(Message(role="system", content=memory_context))
        messages.extend(state.messages)
        return messages

    def _truncate_text(self, content: str) -> str:
        if len(content) <= self._max_tool_result_chars:
            return content

        omitted = len(content) - self._max_tool_result_chars
        return (
            content[: self._max_tool_result_chars]
            + f"\n\n[truncated {omitted} chars to protect context window]"
        )

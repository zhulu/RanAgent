from __future__ import annotations

from agent_app.core.messages import Message
from agent_app.core.state import SessionState
from agent_app.llm.base import LLMBackend
from agent_app.memory.session_store import JsonSessionStore
from agent_app.observability.logger import get_logger
from agent_app.skills.registry import SkillRegistry
from agent_app.tools.registry import ToolRegistry


class Agent:
    def __init__(
        self,
        llm: LLMBackend,
        tool_registry: ToolRegistry,
        session_store: JsonSessionStore,
        skill_registry: SkillRegistry | None = None,
        max_tool_iterations: int = 3,
    ) -> None:
        self._llm = llm
        self._tool_registry = tool_registry
        self._session_store = session_store
        self._skill_registry = skill_registry or SkillRegistry([])
        self._max_tool_iterations = max_tool_iterations
        self._logger = get_logger(self.__class__.__name__)

    def run(
        self,
        user_input: str,
        session_id: str = "default",
        skill_names: list[str] | None = None,
    ) -> str:
        state = self._session_store.load(session_id)
        state.add(role="user", content=user_input)

        reply = self._run_loop(state, skill_names=skill_names or [])
        self._session_store.save(state)
        return reply

    def _run_loop(self, state: SessionState, skill_names: list[str]) -> str:
        runtime_messages = self._build_runtime_messages(state, skill_names)
        for _ in range(self._max_tool_iterations):
            decision = self._llm.decide(
                messages=runtime_messages,
                tools=self._tool_registry.specs(),
            )
            if decision.action == "respond":
                content = decision.content or "未生成回复。"
                state.add(role="assistant", content=content)
                return content

            if decision.action != "tool" or not decision.tool_name:
                fallback = "模型返回了无法识别的动作。"
                state.add(role="assistant", content=fallback)
                return fallback

            tool = self._tool_registry.get(decision.tool_name)
            tool_input = decision.tool_input or ""
            self._logger.info("Running tool %s with input: %s", tool.name, tool_input)
            result = tool.run(tool_input)
            state.add(role="tool", content=result.content, name=tool.name)
            runtime_messages = self._build_runtime_messages(state, skill_names)

        fallback = "已达到最大工具调用次数，请缩小问题范围或调整规划策略。"
        state.add(role="assistant", content=fallback)
        return fallback

    def _build_runtime_messages(
        self, state: SessionState, skill_names: list[str]
    ) -> list[Message]:
        messages: list[Message] = []
        for skill in self._skill_registry.resolve(skill_names):
            messages.append(Message(role="system", content=skill.to_system_prompt()))
        messages.extend(state.messages)
        return messages

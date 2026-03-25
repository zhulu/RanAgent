from __future__ import annotations

import re

from agent_app.core.messages import Message
from agent_app.llm.base import LLMDecision, ToolSpec


class MockLLM:
    """A deterministic planner for local debugging without an API key."""

    def decide(self, messages: list[Message], tools: list[ToolSpec]) -> LLMDecision:
        last_message = messages[-1].content.strip()
        loaded_skills = self._extract_skill_names(messages)
        if messages[-1].role == "tool":
            return LLMDecision(
                action="respond",
                content=f"工具执行结果如下：\n{last_message}",
            )

        lowered = last_message.lower()
        if loaded_skills and any(token in lowered for token in ("skill", "skills", "技能")):
            return LLMDecision(
                action="respond",
                content=f"当前已加载技能：{', '.join(loaded_skills)}",
            )

        if any(keyword in last_message for keyword in ("几点", "时间", "现在几号")):
            return LLMDecision(action="tool", tool_name="time_now", tool_input="")

        if re.fullmatch(r"[\d\.\+\-\*\/\(\) ]+", lowered):
            return LLMDecision(
                action="tool",
                tool_name="calculator",
                tool_input=last_message,
            )

        return LLMDecision(
            action="respond",
            content=(
                "这是一个最小 Agent 骨架。当前未命中工具路由，"
                "你可以试试输入“现在几点”、直接输入算式，"
                "或者在加载技能后询问“当前有哪些技能”。"
            ),
        )

    @staticmethod
    def _extract_skill_names(messages: list[Message]) -> list[str]:
        names: list[str] = []
        prefix = "Skill Name: "
        for message in messages:
            if message.role != "system":
                continue
            for line in message.content.splitlines():
                if line.startswith(prefix):
                    names.append(line.removeprefix(prefix).strip())
        return names

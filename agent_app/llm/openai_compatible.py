from __future__ import annotations

import json

from agent_app.config import ModelConfig
from agent_app.core.messages import Message
from agent_app.llm.base import LLMDecision, ToolSpec


class OpenAICompatibleLLM:
    """Thin wrapper around the OpenAI Python SDK for simple agent planning."""

    def __init__(
        self,
        model_name: str,
        api_key: str,
        base_url: str | None = None,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "openai package is required for non-mock backends. "
                "Install it with: pip install openai"
            ) from exc

        client_kwargs: dict[str, str] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = OpenAI(**client_kwargs)
        self._model_name = model_name
        self._base_url = base_url

    @classmethod
    def from_model_config(cls, model_config: ModelConfig) -> "OpenAICompatibleLLM":
        model_config.validate()
        return cls(
            model_name=model_config.model_name,
            api_key=model_config.api_key or "",
            base_url=model_config.base_url,
        )

    def decide(self, messages: list[Message], tools: list[ToolSpec]) -> LLMDecision:
        tool_lines = "\n".join(f"- {tool.name}: {tool.description}" for tool in tools)
        system_prompt = (
            "你是一个 Agent Planner。"
            "你只能输出 JSON，不要输出任何额外文本。"
            '如果需要调用工具，输出 {"action":"tool","tool_name":"...","tool_input":"..."}。'
            '如果可以直接回复，输出 {"action":"respond","content":"..."}。'
            "对于需要多个字段的工具入参，请把 tool_input 写成 JSON 字符串。"
            "可用工具如下：\n"
            f"{tool_lines}"
        )

        sdk_messages = [{"role": "system", "content": system_prompt}]
        for message in messages:
            sdk_role = message.role if message.role in {"user", "assistant", "system"} else "user"
            sdk_messages.append({"role": sdk_role, "content": message.content})

        response = self._client.chat.completions.create(
            model=self._model_name,
            messages=sdk_messages,
            response_format={"type": "json_object"},
        )
        payload = response.choices[0].message.content or "{}"
        data = json.loads(payload)

        return LLMDecision(
            action=data["action"],
            content=data.get("content"),
            tool_name=data.get("tool_name"),
            tool_input=data.get("tool_input"),
        )

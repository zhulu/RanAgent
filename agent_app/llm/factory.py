from __future__ import annotations

from agent_app.config import ModelConfig
from agent_app.llm.base import LLMBackend
from agent_app.llm.mock import MockLLM
from agent_app.llm.openai_compatible import OpenAICompatibleLLM


def build_llm_backend(model_config: ModelConfig) -> LLMBackend:
    if model_config.is_mock:
        return MockLLM()
    return OpenAICompatibleLLM.from_model_config(model_config)

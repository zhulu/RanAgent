from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProviderPreset:
    provider: str
    model_name: str
    base_url: str | None
    api_key_env: tuple[str, ...]
    model_env: tuple[str, ...]
    base_url_env: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ModelConfig:
    provider: str
    model_name: str
    api_key: str | None
    base_url: str | None
    api_key_sources: tuple[str, ...]

    @property
    def is_mock(self) -> bool:
        return self.provider == "mock"

    def validate(self) -> None:
        if not self.is_mock and not self.api_key:
            source_list = ", ".join(self.api_key_sources)
            raise RuntimeError(
                f"{self.provider} provider 缺少 API Key，请设置以下任一环境变量：{source_list}"
            )

    def to_json(self) -> str:
        payload = asdict(self)
        payload["api_key"] = "***" if self.api_key else None
        return json.dumps(payload, ensure_ascii=False, indent=2)


PROVIDER_PRESETS: dict[str, ProviderPreset] = {
    "openai": ProviderPreset(
        provider="openai",
        model_name="gpt-4.1-mini",
        base_url="https://api.openai.com/v1",
        api_key_env=("OPENAI_API_KEY",),
        model_env=("OPENAI_MODEL_NAME",),
        base_url_env=("OPENAI_BASE_URL",),
    ),
    "gemini": ProviderPreset(
        provider="gemini",
        model_name="gemini-2.5-flash",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key_env=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        model_env=("GEMINI_MODEL_NAME",),
        base_url_env=("GEMINI_BASE_URL",),
    ),
    "glm": ProviderPreset(
        provider="glm",
        model_name="glm-4.7",
        base_url="https://api.z.ai/api/paas/v4/",
        api_key_env=("GLM_API_KEY", "ZAI_API_KEY"),
        model_env=("GLM_MODEL_NAME",),
        base_url_env=("GLM_BASE_URL", "ZAI_BASE_URL"),
    ),
}


@dataclass(slots=True)
class Settings:
    model_provider: str
    model_name_override: str | None
    api_key_override: str | None
    base_url_override: str | None
    max_tool_iterations: int
    session_store_dir: Path
    workspace_root: Path
    skills_dir: Path

    def resolve_model_config(self) -> ModelConfig:
        return resolve_model_config(
            provider=self.model_provider,
            model_name_override=self.model_name_override,
            api_key_override=self.api_key_override,
            base_url_override=self.base_url_override,
        )


def get_settings(
    *,
    model_provider: str | None = None,
    model_name_override: str | None = None,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> Settings:
    return Settings(
        model_provider=(
            model_provider
            or os.getenv("AGENT_MODEL_PROVIDER")
            or os.getenv("AGENT_MODEL_BACKEND")
            or "mock"
        ),
        model_name_override=model_name_override or os.getenv("AGENT_MODEL_NAME"),
        api_key_override=api_key_override or os.getenv("AGENT_API_KEY"),
        base_url_override=base_url_override or os.getenv("AGENT_BASE_URL"),
        max_tool_iterations=int(os.getenv("AGENT_MAX_TOOL_ITERATIONS", "3")),
        session_store_dir=Path(
            os.getenv("AGENT_SESSION_STORE_DIR", ".agent_state/sessions")
        ),
        workspace_root=Path(os.getenv("AGENT_WORKSPACE_ROOT", Path.cwd())),
        skills_dir=Path(os.getenv("AGENT_SKILLS_DIR", "skills")),
    )


def resolve_model_config(
    *,
    provider: str,
    model_name_override: str | None = None,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> ModelConfig:
    normalized_provider = provider.strip().lower()
    if normalized_provider == "glm-4.7":
        normalized_provider = "glm"

    if normalized_provider == "mock":
        return ModelConfig(
            provider="mock",
            model_name="mock",
            api_key=None,
            base_url=None,
            api_key_sources=(),
        )

    if normalized_provider not in PROVIDER_PRESETS:
        supported = ", ".join(["mock", *sorted(PROVIDER_PRESETS)])
        raise ValueError(f"Unsupported provider: {provider}. Supported: {supported}")

    preset = PROVIDER_PRESETS[normalized_provider]
    return ModelConfig(
        provider=preset.provider,
        model_name=(
            model_name_override
            or _first_env_value(preset.model_env)
            or preset.model_name
        ),
        api_key=api_key_override or _first_env_value(preset.api_key_env),
        base_url=base_url_override or _first_env_value(preset.base_url_env) or preset.base_url,
        api_key_sources=preset.api_key_env,
    )


def _first_env_value(names: tuple[str, ...]) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None

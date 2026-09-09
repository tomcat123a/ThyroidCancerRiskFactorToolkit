from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .path_utils import find_project_root, resolve_config_path


@dataclass(frozen=True)
class LlmSettings:
    enabled: bool
    provider: str
    model: str
    api_url: str
    api_key: str
    timeout_seconds: int
    max_workers: int
    thinking_enabled: bool

    @property
    def is_placeholder(self) -> bool:
        api_key = self.api_key.strip().upper()
        api_url = self.api_url.strip().lower()
        return (not self.enabled) or api_key in {"", "YOUR_API_KEY"} or "your-api-url" in api_url


@dataclass(frozen=True)
class AppConfig:
    project_title: str
    author_name: str
    author_email: str
    input_xlsx: Path
    output_dir: Path
    prompt_dir: Path
    agent_data_dir: Path
    demo_umls_lexicon_csv: Path
    demo_country_reference_csv: Path
    llm: LlmSettings
    alternate_llm: LlmSettings
    config_path: Path
    project_root: Path


def _build_llm_settings(raw: dict) -> LlmSettings:
    return LlmSettings(
        enabled=bool(raw.get("enabled", False)),
        provider=str(raw.get("provider", "")).strip(),
        model=str(raw.get("model", "")).strip(),
        api_url=str(raw.get("api_url", "")).strip(),
        api_key=str(raw.get("api_key", "")).strip(),
        timeout_seconds=int(raw.get("timeout_seconds", 120)),
        max_workers=int(raw.get("max_workers", 10)),
        thinking_enabled=bool(raw.get("thinking_enabled", False)),
    )


def load_config() -> AppConfig:
    config_path = resolve_config_path()
    project_root = find_project_root()
    payload = json.loads(config_path.read_text(encoding="utf-8"))

    return AppConfig(
        project_title=str(payload.get("project_title", "")).strip(),
        author_name=str(payload.get("author_name", "")).strip(),
        author_email=str(payload.get("author_email", "")).strip(),
        input_xlsx=(project_root / str(payload.get("input_xlsx", "data/sample/preproc_thca_demo_first100.xlsx"))).resolve(),
        output_dir=(project_root / str(payload.get("output_dir", "outputs"))).resolve(),
        prompt_dir=(project_root / str(payload.get("prompt_dir", "prompt"))).resolve(),
        agent_data_dir=(project_root / str(payload.get("agent_data_dir", "agent_data"))).resolve(),
        demo_umls_lexicon_csv=(project_root / str(payload.get("demo_umls_lexicon_csv", "data/demo_resources/umls_concepts_demo.csv"))).resolve(),
        demo_country_reference_csv=(project_root / str(payload.get("demo_country_reference_csv", "data/demo_resources/country_continent_reference.csv"))).resolve(),
        llm=_build_llm_settings(payload.get("llm", {})),
        alternate_llm=_build_llm_settings(payload.get("alternate_llm", {})),
        config_path=config_path.resolve(),
        project_root=project_root,
    )

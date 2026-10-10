from __future__ import annotations

import json
from pathlib import Path

import requests

from .config import LlmSettings
from .io_utils import new_run_directory, write_json, write_text


class LlmClient:
    """Non-streaming, temperature-0 LLM client with JSON logging.

    Matches the manuscript's "Prompt engineering and model control" section:
    generation is non-streaming, ``temperature=0.0``, and every request/response
    pair is logged under ``agent_data/`` for TRIPOD-LLM traceability.

    Two transport profiles are supported:

    * ``openai_compatible`` — any OpenAI-style ``/chat/completions`` endpoint.
      Used for the manuscript's DeepSeek-V4-Pro and Doubao-1.8-Seed annotators.
    * ``gemini_compatible`` — a Gemini ``generateContent`` endpoint.  Used for
      the manuscript's Gemini-3-Pro adjudicator / long-context semantic
      clustering model.

    To use it, fill ``model``, ``api_url`` and ``api_key`` in ``config.json``
    (the provider field only selects the transport, not a hard-coded vendor).
    """

    def __init__(self, settings: LlmSettings, agent_data_root: Path) -> None:
        self.settings = settings
        self.run_dir = new_run_directory(agent_data_root, "llm_requests")

    @property
    def enabled(self) -> bool:
        return not self.settings.is_placeholder

    def complete_json(self, prompt_name: str, prompt_text: str) -> dict | list | None:
        if not self.enabled:
            return None
        response_text = self._request(prompt_text)
        prompt_dir = new_run_directory(self.run_dir, prompt_name)
        write_text(prompt_dir / "prompt.txt", prompt_text)
        write_text(prompt_dir / "response.txt", response_text)
        parsed = _extract_json(response_text)
        write_json(prompt_dir / "parsed.json", parsed if parsed is not None else {"raw_response": response_text})
        return parsed

    def _request(self, prompt_text: str) -> str:
        if self.settings.provider in {"openai_compatible", "deepseek", "deepseek_v3_2", "doubao"}:
            return self._call_openai_compatible(prompt_text)
        if self.settings.provider in {"gemini_compatible", "gemini", "gemini_3_pro"}:
            return self._call_gemini_compatible(prompt_text)
        raise ValueError(f"Unsupported provider: {self.settings.provider}")

    def _call_openai_compatible(self, prompt_text: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.model,
            "stream": False,
            "temperature": 0.0,
            "messages": [{"role": "user", "content": prompt_text}],
            "response_format": {"type": "json_object"},
        }
        response = requests.post(
            self.settings.api_url,
            headers=headers,
            json=payload,
            timeout=self.settings.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return str(data["choices"][0]["message"]["content"])

    def _call_gemini_compatible(self, prompt_text: str) -> str:
        headers = {"Content-Type": "application/json"}
        api_url = self.settings.api_url
        if "key=" not in api_url:
            delimiter = "&" if "?" in api_url else "?"
            api_url = f"{api_url}{delimiter}key={self.settings.api_key}"
        payload = {
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.0},
            "contents": [{"parts": [{"text": prompt_text}]}],
        }
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=self.settings.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return str(data["candidates"][0]["content"]["parts"][0]["text"])


def _extract_json(text: str) -> dict | list | None:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    if "```json" in text:
        start = text.find("```json") + len("```json")
        end = text.rfind("```")
        if end > start:
            snippet = text[start:end].strip()
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                return None
    return None

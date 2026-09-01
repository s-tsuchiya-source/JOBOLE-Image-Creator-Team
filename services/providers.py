from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import mimetypes
import os
from pathlib import Path
import re
from typing import Any


JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


@dataclass
class ProviderResult:
    data: dict
    input_tokens: int = 0
    output_tokens: int = 0
    provider: str = ""
    model: str = ""


def parse_json_text(text: str) -> dict:
    cleaned = JSON_FENCE_RE.sub("", text.strip()).strip()
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("AI output did not contain a JSON object.")
        result = json.loads(cleaned[start : end + 1])
    if not isinstance(result, dict):
        raise ValueError("AI output root must be a JSON object.")
    return result


def _image_data(path: Path) -> tuple[str, str]:
    media_type = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return media_type, encoded


class AnthropicProvider:
    def __init__(self, model: str | None = None):
        from anthropic import Anthropic

        self.model = model or os.getenv("ANTHROPIC_MODEL")
        if not self.model:
            raise ValueError("ANTHROPIC_MODEL is not configured.")
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY is not configured.")
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    @staticmethod
    def _format_instruction(schema: dict) -> str:
        return (
            "Return exactly one JSON object and no prose or markdown. "
            "The JSON must satisfy this JSON Schema:\n"
            + json.dumps(schema, ensure_ascii=False)
        )

    @staticmethod
    def _to_result(message, model: str) -> ProviderResult:
        text_parts = [
            block.text
            for block in message.content
            if getattr(block, "type", None) == "text"
        ]
        usage = getattr(message, "usage", None)
        return ProviderResult(
            data=parse_json_text("\n".join(text_parts)),
            input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
            provider="anthropic",
            model=model,
        )

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        max_tokens: int = 8192,
    ) -> ProviderResult:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt + "\n\n" + self._format_instruction(schema),
            messages=[{"role": "user", "content": user_prompt}],
        )
        return self._to_result(message, self.model)

    def generate_json_with_image(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        image_path: Path,
        max_tokens: int = 8192,
    ) -> ProviderResult:
        media_type, encoded = _image_data(image_path)
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt + "\n\n" + self._format_instruction(schema),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": encoded,
                            },
                        },
                        {"type": "text", "text": user_prompt},
                    ],
                }
            ],
        )
        return self._to_result(message, self.model)


class OpenAIProvider:
    def __init__(self, model: str | None = None):
        from openai import OpenAI

        self.model = model or os.getenv("OPENAI_CCO_MODEL")
        if not self.model:
            raise ValueError("OPENAI_CCO_MODEL is not configured.")
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is not configured.")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    @staticmethod
    def _build_prompt(system_prompt: str, user_prompt: str, schema: dict) -> str:
        return (
            system_prompt
            + "\n\nReturn exactly one JSON object and no prose or markdown. "
            + "The JSON must satisfy this JSON Schema:\n"
            + json.dumps(schema, ensure_ascii=False)
            + "\n\nINPUT:\n"
            + user_prompt
        )

    def _to_result(self, response) -> ProviderResult:
        usage = getattr(response, "usage", None)
        return ProviderResult(
            data=parse_json_text(response.output_text),
            input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
            provider="openai",
            model=self.model,
        )

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        max_tokens: int = 8192,
    ) -> ProviderResult:
        response = self.client.responses.create(
            model=self.model,
            input=self._build_prompt(system_prompt, user_prompt, schema),
            max_output_tokens=max_tokens,
        )
        return self._to_result(response)

    def generate_json_with_image(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        image_path: Path,
        max_tokens: int = 8192,
    ) -> ProviderResult:
        media_type, encoded = _image_data(image_path)
        data_url = f"data:{media_type};base64,{encoded}"
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": self._build_prompt(system_prompt, user_prompt, schema),
                        },
                        {"type": "input_image", "image_url": data_url},
                    ],
                }
            ],
            max_output_tokens=max_tokens,
        )
        return self._to_result(response)


class DryRunProvider:
    """Does not invent production outputs; records that a live provider is required."""

    def generate_json(self, **_: Any) -> ProviderResult:
        raise RuntimeError(
            "dry-run mode does not generate AI decisions. Configure API keys and set "
            "PRODUCTION_MODE=live to execute AI stages."
        )

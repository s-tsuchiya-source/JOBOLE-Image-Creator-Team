from __future__ import annotations

from dataclasses import dataclass
import json
import os
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


class AnthropicProvider:
    def __init__(self, model: str | None = None):
        from anthropic import Anthropic

        self.model = model or os.getenv("ANTHROPIC_MODEL")
        if not self.model:
            raise ValueError("ANTHROPIC_MODEL is not configured.")
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY is not configured.")
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        max_tokens: int = 8192,
    ) -> ProviderResult:
        schema_text = json.dumps(schema, ensure_ascii=False)
        format_instruction = (
            "Return exactly one JSON object and no prose or markdown. "
            "The JSON must satisfy this JSON Schema:\n" + schema_text
        )
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt + "\n\n" + format_instruction,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text_parts = [
            block.text
            for block in message.content
            if getattr(block, "type", None) == "text"
        ]
        text = "\n".join(text_parts)
        usage = getattr(message, "usage", None)
        return ProviderResult(
            data=parse_json_text(text),
            input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
            provider="anthropic",
            model=self.model,
        )


class OpenAIProvider:
    def __init__(self, model: str | None = None):
        from openai import OpenAI

        self.model = model or os.getenv("OPENAI_CCO_MODEL")
        if not self.model:
            raise ValueError("OPENAI_CCO_MODEL is not configured.")
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is not configured.")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        max_tokens: int = 8192,
    ) -> ProviderResult:
        schema_text = json.dumps(schema, ensure_ascii=False)
        prompt = (
            system_prompt
            + "\n\nReturn exactly one JSON object and no prose or markdown. "
            + "The JSON must satisfy this JSON Schema:\n"
            + schema_text
            + "\n\nINPUT:\n"
            + user_prompt
        )
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            max_output_tokens=max_tokens,
        )
        usage = getattr(response, "usage", None)
        return ProviderResult(
            data=parse_json_text(response.output_text),
            input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
            provider="openai",
            model=self.model,
        )


class DryRunProvider:
    """Does not invent production outputs; records that a live provider is required."""

    def generate_json(self, **_: Any) -> ProviderResult:
        raise RuntimeError(
            "dry-run mode does not generate AI decisions. Configure API keys and set "
            "PRODUCTION_MODE=live to execute AI stages."
        )

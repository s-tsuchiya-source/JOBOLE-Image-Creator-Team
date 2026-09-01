from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.agent_runner import load_agent_config, read_repo_file
from services.providers import ClaudeCodeProvider, ProviderResult
from services.schema_validator import load_schema, validate_data


def review_image(
    *,
    image_path: Path,
    context: dict[str, Any],
    provider: ClaudeCodeProvider | None = None,
) -> ProviderResult:
    agent = load_agent_config("creative_reviewer")
    system_prompt = read_repo_file(agent["file"])
    schema = load_schema(agent["schema"])
    provider = provider or ClaudeCodeProvider()
    user_prompt = (
        "Review the supplied generated recruitment creative independently. "
        "Compare the pixels/text in the image with every approved upstream artifact. "
        "Return root cause and return_to_agent for each problem.\n\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )
    result = provider.generate_json_with_image(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        schema=schema,
        image_path=image_path,
    )
    validate_data(result.data, schema)
    return result

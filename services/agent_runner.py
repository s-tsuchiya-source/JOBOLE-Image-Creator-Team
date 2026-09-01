from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from services.providers import ClaudeCodeProvider, ProviderResult
from services.schema_validator import load_schema, validate_data


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_CONFIG = REPO_ROOT / "configs" / "agents.yaml"


def load_agent_config(agent_name: str) -> dict:
    config = yaml.safe_load(AGENTS_CONFIG.read_text(encoding="utf-8")) or {}
    agents = config.get("agents", {})
    aliases = config.get("legacy_aliases", {})
    resolved_name = aliases.get(agent_name, agent_name)
    if resolved_name not in agents:
        raise KeyError(f"Unknown agent: {agent_name}")
    result = dict(agents[resolved_name])
    result["name"] = resolved_name
    return result


def read_repo_file(path_value: str) -> str:
    return (REPO_ROOT / path_value).read_text(encoding="utf-8")


def build_user_prompt(context: dict[str, Any], task: str) -> str:
    return (
        "<context>\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
        + "\n</context>\n\n<task>\n"
        + task
        + "\n</task>"
    )


def run_claude_agent(
    agent_name: str,
    *,
    context: dict[str, Any],
    task: str,
    provider: ClaudeCodeProvider | None = None,
) -> ProviderResult:
    """Execute one specialist via Claude Code subscription login.

    No ANTHROPIC_API_KEY is required. The provider intentionally removes any
    inherited ANTHROPIC_API_KEY before launching Claude Code so a stale key
    cannot silently switch the run to pay-as-you-go API billing.
    """
    agent = load_agent_config(agent_name)
    system_prompt = read_repo_file(agent["file"])
    schema = load_schema(agent["schema"])
    provider = provider or ClaudeCodeProvider()
    result = provider.generate_json(
        system_prompt=system_prompt,
        user_prompt=build_user_prompt(context, task),
        schema=schema,
    )
    validate_data(result.data, schema)
    return result

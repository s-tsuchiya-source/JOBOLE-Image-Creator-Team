from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


@dataclass
class ProviderResult:
    data: dict
    input_tokens: int = 0
    output_tokens: int = 0
    provider: str = ""
    model: str = ""
    incremental_cost_yen: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


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


def _resolve_executable(command: str) -> str:
    resolved = shutil.which(command)
    if not resolved:
        raise RuntimeError(
            f"Command not found: {command}. Install it and sign in before production."
        )
    return resolved


def _windows_safe_command(executable: str, args: list[str]) -> list[str]:
    """Run npm-generated .cmd/.bat launchers reliably from Python on Windows."""
    suffix = Path(executable).suffix.lower()
    if os.name == "nt" and suffix in {".cmd", ".bat"}:
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        return [comspec, "/d", "/s", "/c", executable, *args]
    return [executable, *args]


def _subscription_env(*blocked_keys: str) -> dict[str, str]:
    """Prevent accidental PAYG auth when subscription-login CLI use is intended."""
    env = dict(os.environ)
    for key in blocked_keys:
        env.pop(key, None)
    return env


def _run_cli(
    *,
    command: str,
    args: list[str],
    stdin_text: str,
    timeout_seconds: int,
    env: dict[str, str],
    cwd: Path = REPO_ROOT,
) -> subprocess.CompletedProcess[str]:
    executable = _resolve_executable(command)
    argv = _windows_safe_command(executable, args)
    try:
        completed = subprocess.run(
            argv,
            input=stdin_text,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(cwd),
            env=env,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"{command} timed out after {timeout_seconds}s."
        ) from exc
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        detail = stderr or stdout or f"exit code {completed.returncode}"
        raise RuntimeError(f"{command} failed: {detail}")
    return completed


class ClaudeCodeProvider:
    """Claude specialist provider using Claude Code subscription login, not Anthropic API."""

    def __init__(self, model: str | None = None):
        self.command = os.getenv("CLAUDE_CLI_COMMAND", "claude")
        self.model = model or os.getenv("CLAUDE_CLI_MODEL", "opus")
        self.timeout_seconds = int(os.getenv("CLAUDE_CLI_TIMEOUT_SEC", "600"))
        self.max_turns = int(os.getenv("CLAUDE_CLI_MAX_TURNS", "4"))

    @staticmethod
    def _build_stdin_prompt(system_prompt: str, user_prompt: str, schema: dict) -> str:
        # Keep the command line short on Windows. Role instructions, source context,
        # and schema can be large, so all of them travel through stdin.
        return (
            "<specialist_role>\n"
            + system_prompt
            + "\n</specialist_role>\n\n"
            + "<required_output>\nReturn exactly one JSON object and no prose or markdown. "
            + "The JSON must satisfy this JSON Schema exactly:\n"
            + json.dumps(schema, ensure_ascii=False)
            + "\n</required_output>\n\n"
            + "<work_input>\n"
            + user_prompt
            + "\n</work_input>"
        )

    def _execute(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        image_path: Path | None = None,
    ) -> ProviderResult:
        args = [
            "-p",
            "--output-format",
            "json",
            "--model",
            self.model,
            "--max-turns",
            str(self.max_turns),
        ]
        prompt = self._build_stdin_prompt(system_prompt, user_prompt, schema)
        if image_path is not None:
            image_path = image_path.resolve()
            args.extend(["--add-dir", str(image_path.parent)])
            prompt += (
                "\n\n<image_review_requirement>\n"
                "Visually inspect the local image file using the Read tool before answering. "
                f"Image path: {image_path}\n"
                "</image_review_requirement>"
            )

        completed = _run_cli(
            command=self.command,
            args=args,
            stdin_text=prompt,
            timeout_seconds=self.timeout_seconds,
            # Explicitly remove ANTHROPIC_API_KEY so Claude Code uses the logged-in
            # Claude subscription instead of PAYG Console billing.
            env=_subscription_env("ANTHROPIC_API_KEY"),
        )
        raw_stdout = (completed.stdout or "").strip()
        try:
            wrapper = json.loads(raw_stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Claude Code did not return valid --output-format json output. "
                f"stdout={raw_stdout[:1000]!r}"
            ) from exc
        if wrapper.get("is_error"):
            raise RuntimeError(f"Claude Code returned an error: {wrapper}")
        result_text = wrapper.get("result")
        if not isinstance(result_text, str):
            raise RuntimeError("Claude Code JSON output did not contain a string result field.")
        return ProviderResult(
            data=parse_json_text(result_text),
            provider="claude_code",
            model=self.model,
            incremental_cost_yen=0.0,
            metadata={
                "session_id": wrapper.get("session_id"),
                "num_turns": wrapper.get("num_turns"),
                "duration_ms": wrapper.get("duration_ms"),
                "billing_mode": "subscription_login",
            },
        )

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        max_tokens: int = 8192,
    ) -> ProviderResult:
        del max_tokens
        return self._execute(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
        )

    def generate_json_with_image(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        image_path: Path,
        max_tokens: int = 8192,
    ) -> ProviderResult:
        del max_tokens
        return self._execute(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
            image_path=image_path,
        )


class CodexCliProvider:
    """Codex CCO provider using Codex CLI + ChatGPT login, not OPENAI_API_KEY."""

    def __init__(self, model: str | None = None):
        self.command = os.getenv("CODEX_CLI_COMMAND", "codex")
        self.model = model if model is not None else os.getenv("CODEX_CLI_MODEL", "").strip()
        self.timeout_seconds = int(os.getenv("CODEX_CLI_TIMEOUT_SEC", "900"))
        self.sandbox = os.getenv("CODEX_CLI_SANDBOX", "read-only")

    @staticmethod
    def _build_prompt(system_prompt: str, user_prompt: str, schema: dict) -> str:
        return (
            system_prompt
            + "\n\nReturn exactly one JSON object and no prose or markdown. "
            + "Your final JSON must satisfy the supplied output schema."
            + "\n\nINPUT:\n"
            + user_prompt
            + "\n\nSCHEMA REFERENCE:\n"
            + json.dumps(schema, ensure_ascii=False)
        )

    def _execute(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        image_path: Path | None = None,
    ) -> ProviderResult:
        prompt = self._build_prompt(system_prompt, user_prompt, schema)
        with tempfile.TemporaryDirectory(prefix="jobole_codex_") as tmpdir:
            tmp = Path(tmpdir)
            schema_path = tmp / "output-schema.json"
            output_path = tmp / "last-message.json"
            schema_path.write_text(
                json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            args = [
                "exec",
                "--ephemeral",
                "--sandbox",
                self.sandbox,
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
            ]
            if self.model:
                args.extend(["--model", self.model])
            if image_path is not None:
                args.extend(["--image", str(image_path.resolve())])
            # Explicit '-' forces prompt input from stdin. This also avoids the
            # Windows optional-stdin ambiguity of a positional prompt.
            args.append("-")

            completed = _run_cli(
                command=self.command,
                args=args,
                stdin_text=prompt,
                timeout_seconds=self.timeout_seconds,
                # OPENAI_API_KEY may exist solely for the image API. Do not expose
                # it to Codex CLI; force use of the stored ChatGPT login instead.
                env=_subscription_env("OPENAI_API_KEY"),
            )
            if output_path.exists():
                final_text = output_path.read_text(encoding="utf-8-sig")
            else:
                final_text = completed.stdout or ""

        return ProviderResult(
            data=parse_json_text(final_text),
            provider="codex_cli",
            model=self.model or "chatgpt_default",
            incremental_cost_yen=0.0,
            metadata={"billing_mode": "chatgpt_login"},
        )

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        max_tokens: int = 8192,
    ) -> ProviderResult:
        del max_tokens
        return self._execute(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
        )

    def generate_json_with_image(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
        image_path: Path,
        max_tokens: int = 8192,
    ) -> ProviderResult:
        del max_tokens
        return self._execute(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
            image_path=image_path,
        )


class DryRunProvider:
    def generate_json(self, **_: Any) -> ProviderResult:
        raise RuntimeError(
            "dry-run mode does not generate AI decisions. Sign in to Codex/Claude Code "
            "and run production without --dry-run to execute AI stages."
        )

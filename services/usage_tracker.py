from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from pathlib import Path

from services.providers import ProviderResult


@dataclass
class UsageEntry:
    timestamp: str
    stage: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    image_generations: int
    estimated_cost_yen: float | None
    billing_mode: str = ""


def _float_env(name: str) -> float | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return float(value)


def validate_live_cost_configuration() -> None:
    """Validate only the image backend that can create incremental API spend."""
    if os.getenv("PRODUCTION_MODE", "dry-run").lower() != "live":
        return
    backend = os.getenv("IMAGE_BACKEND", "openvino_ovms").strip().lower()
    local_backends = {
        "local",
        "local_webui",
        "webui",
        "forge",
        "automatic1111",
        "openvino",
        "openvino_ovms",
        "ovms",
        "intel_openvino",
    }
    if backend in local_backends:
        return
    if backend not in {"openai", "openai_api"}:
        raise SystemExit(f"Unsupported IMAGE_BACKEND={backend!r}")

    required = (
        "OPENAI_API_KEY",
        "OPENAI_IMAGE_MODEL",
        "USDJPY_RATE",
        "OPENAI_IMAGE_ESTIMATED_USD_PER_GENERATION",
    )
    missing = [name for name in required if not (os.getenv(name) or "").strip()]
    invalid = []
    for name in ("USDJPY_RATE", "OPENAI_IMAGE_ESTIMATED_USD_PER_GENERATION"):
        raw = (os.getenv(name) or "").strip()
        if not raw:
            continue
        try:
            if float(raw) <= 0:
                invalid.append(name)
        except ValueError:
            invalid.append(name)
    if missing or invalid:
        lines = []
        if missing:
            lines.append("未設定: " + ", ".join(missing))
        if invalid:
            lines.append("0より大きい数値が必要: " + ", ".join(invalid))
        raise SystemExit(
            "OpenAI画像APIモードを開始できません。\n"
            + "\n".join(lines)
            + "\nテキストAI用APIキーは不要です。"
        )


def estimate_text_cost_yen(result: ProviderResult) -> float | None:
    if result.provider in {"claude_code", "codex_cli"}:
        return 0.0
    return float(result.incremental_cost_yen)


class UsageTracker:
    def __init__(self, project_dir: Path):
        validate_live_cost_configuration()
        self.path = project_dir / "04_project_review" / "provider-usage.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record_text(self, stage: str, result: ProviderResult) -> UsageEntry:
        entry = UsageEntry(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            stage=stage,
            provider=result.provider,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            image_generations=0,
            estimated_cost_yen=estimate_text_cost_yen(result),
            billing_mode=str(result.metadata.get("billing_mode") or "subscription_login"),
        )
        self._append(entry)
        return entry

    def record_image(
        self,
        stage: str,
        provider: str,
        model: str,
        count: int = 1,
    ) -> UsageEntry:
        normalized = provider.strip().lower()
        local_providers = {
            "local",
            "local_webui",
            "webui",
            "forge",
            "automatic1111",
            "openvino",
            "openvino_ovms",
            "ovms",
            "intel_openvino",
        }
        if normalized in local_providers:
            cost = 0.0
            billing_mode = "local_compute"
        elif normalized in {"openai", "openai_api", "openai_image_api"}:
            usd_jpy = _float_env("USDJPY_RATE")
            unit_usd = _float_env("OPENAI_IMAGE_ESTIMATED_USD_PER_GENERATION")
            cost = None
            if usd_jpy is not None and unit_usd is not None:
                cost = round(unit_usd * count * usd_jpy, 4)
            billing_mode = "api_usage"
        else:
            cost = None
            billing_mode = "unknown"

        entry = UsageEntry(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            stage=stage,
            provider=provider,
            model=model,
            input_tokens=0,
            output_tokens=0,
            image_generations=count,
            estimated_cost_yen=cost,
            billing_mode=billing_mode,
        )
        self._append(entry)
        return entry

    def total_estimated_cost_yen(self) -> float | None:
        if not self.path.exists():
            return 0.0
        total = 0.0
        unknown = False
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            value = json.loads(line).get("estimated_cost_yen")
            if value is None:
                unknown = True
            else:
                total += float(value)
        return None if unknown else round(total, 4)

    def _append(self, entry: UsageEntry) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

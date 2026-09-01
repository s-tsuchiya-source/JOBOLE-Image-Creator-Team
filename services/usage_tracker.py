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


def _float_env(name: str) -> float | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return float(value)


def estimate_text_cost_yen(result: ProviderResult) -> float | None:
    usd_jpy = _float_env("USDJPY_RATE")
    if usd_jpy is None:
        return None

    if result.provider == "anthropic":
        input_rate = _float_env("ANTHROPIC_INPUT_USD_PER_M")
        output_rate = _float_env("ANTHROPIC_OUTPUT_USD_PER_M")
    elif result.provider == "openai":
        input_rate = _float_env("OPENAI_CCO_INPUT_USD_PER_M")
        output_rate = _float_env("OPENAI_CCO_OUTPUT_USD_PER_M")
    else:
        return None

    if input_rate is None or output_rate is None:
        return None
    usd = (result.input_tokens / 1_000_000) * input_rate
    usd += (result.output_tokens / 1_000_000) * output_rate
    return round(usd * usd_jpy, 4)


class UsageTracker:
    def __init__(self, project_dir: Path):
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
        )
        self._append(entry)
        return entry

    def record_image(self, stage: str, provider: str, model: str, count: int = 1) -> UsageEntry:
        usd_jpy = _float_env("USDJPY_RATE")
        unit_usd = _float_env("OPENAI_IMAGE_ESTIMATED_USD_PER_GENERATION")
        cost = None
        if usd_jpy is not None and unit_usd is not None:
            cost = round(unit_usd * count * usd_jpy, 4)
        entry = UsageEntry(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            stage=stage,
            provider=provider,
            model=model,
            input_tokens=0,
            output_tokens=0,
            image_generations=count,
            estimated_cost_yen=cost,
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

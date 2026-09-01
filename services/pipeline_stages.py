from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.agent_runner import run_claude_agent
from services.deterministic_checks import (
    QualityCheckError,
    check_art_direction,
    check_copy_direction,
    check_production_plan,
)
from services.quality_gate import run_codex_gate
from services.usage_tracker import UsageTracker


class PipelineStop(RuntimeError):
    def __init__(self, decision: str, detail: str):
        super().__init__(detail)
        self.decision = decision
        self.detail = detail


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )


def _gate_feedback(gate: dict) -> str:
    issues = gate.get("issues") or []
    if not issues:
        return gate.get("next_action") or "Revise the output to satisfy the Quality Gate."
    return "\n".join(
        f"- {item.get('code')}: {item.get('description')} (return_to={item.get('return_to')})"
        for item in issues
    )


def _handle_non_revision(decision: str, gate: dict) -> None:
    if decision == "pass" or decision == "revise":
        return
    raise PipelineStop(decision, gate.get("next_action") or f"Gate decision: {decision}")


def run_recruitment_stage(
    *,
    project_dir: Path,
    original_request: dict[str, Any],
    tracker: UsageTracker,
    max_revisions: int,
) -> tuple[dict, dict]:
    feedback = ""
    latest = None
    latest_gate = None
    for attempt in range(max_revisions + 1):
        task = "Extract recruitment facts with evidence. Do not create copy or visual ideas."
        if feedback:
            task += "\nCodex Fact Gate feedback from the previous attempt:\n" + feedback
        result = run_claude_agent(
            "recruitment_analyst",
            context=original_request,
            task=task,
        )
        tracker.record_text(f"recruitment_analysis:v{attempt + 1}", result)
        latest = result.data
        save_json(
            project_dir / "01_strategy" / "recruitment" / f"recruitment-analysis-v{attempt + 1:02d}.json",
            latest,
        )
        save_json(project_dir / "01_strategy" / "recruitment" / "recruitment-analysis.json", latest)

        gate_result = run_codex_gate(
            "fact_gate",
            original_request=original_request,
            upstream_outputs={"recruitment_analysis": latest},
        )
        tracker.record_text(f"codex_fact_gate:v{attempt + 1}", gate_result)
        latest_gate = gate_result.data
        save_json(
            project_dir / "01_strategy" / "quality_gates" / f"fact-gate-v{attempt + 1:02d}.json",
            latest_gate,
        )
        save_json(project_dir / "01_strategy" / "quality_gates" / "fact-gate.json", latest_gate)
        decision = latest_gate.get("decision")
        if decision == "pass":
            return latest, latest_gate
        _handle_non_revision(decision, latest_gate)
        feedback = _gate_feedback(latest_gate)

    raise PipelineStop("needs_human_review", "Fact Gate revision limit reached.")


def run_strategy_stage(
    *,
    project_dir: Path,
    original_request: dict[str, Any],
    recruitment: dict,
    fact_gate: dict,
    requested_quantity: int,
    tracker: UsageTracker,
    max_revisions: int,
) -> tuple[dict, dict]:
    feedback = ""
    latest = None
    latest_gate = None
    context = {
        "original_request": original_request,
        "recruitment_analysis": recruitment,
        "fact_gate": fact_gate,
        "requested_quantity": requested_quantity,
    }
    for attempt in range(max_revisions + 1):
        task = (
            "Create a competition-based production plan. Generate at least five meaningful "
            "candidate axes, compare them, and make creative group quantities sum exactly "
            "to requested_quantity."
        )
        if feedback:
            task += "\nPrevious validation/Gate feedback:\n" + feedback
        result = run_claude_agent("production_director", context=context, task=task)
        tracker.record_text(f"production_strategy:v{attempt + 1}", result)
        latest = result.data
        save_json(project_dir / "01_strategy" / f"production-plan-v{attempt + 1:02d}.json", latest)
        save_json(project_dir / "01_strategy" / "production-plan.json", latest)

        try:
            check_production_plan(latest)
        except QualityCheckError as exc:
            feedback = f"Deterministic validation failed: {exc}"
            continue

        gate_result = run_codex_gate(
            "strategy_gate",
            original_request=original_request,
            upstream_outputs={
                "recruitment_analysis": recruitment,
                "fact_gate": fact_gate,
                "production_plan": latest,
            },
        )
        tracker.record_text(f"codex_strategy_gate:v{attempt + 1}", gate_result)
        latest_gate = gate_result.data
        save_json(
            project_dir / "01_strategy" / "quality_gates" / f"strategy-gate-v{attempt + 1:02d}.json",
            latest_gate,
        )
        save_json(project_dir / "01_strategy" / "quality_gates" / "strategy-gate.json", latest_gate)
        decision = latest_gate.get("decision")
        if decision == "pass":
            return latest, latest_gate
        _handle_non_revision(decision, latest_gate)
        feedback = _gate_feedback(latest_gate)

    raise PipelineStop("needs_human_review", "Strategy Gate revision limit reached.")


def run_direction_stage(
    *,
    project_dir: Path,
    original_request: dict[str, Any],
    recruitment: dict,
    production_plan: dict,
    creative_group: dict,
    tracker: UsageTracker,
    max_revisions: int,
) -> dict:
    group_id = creative_group["creative_group_id"]
    feedback = ""
    base_context = {
        "original_request": original_request,
        "recruitment_analysis": recruitment,
        "production_plan": production_plan,
        "creative_group": creative_group,
    }

    for attempt in range(max_revisions + 1):
        copy_task = (
            "Generate at least three materially different copy candidates, select one, "
            "and trace every factual claim to Recruitment Analysis."
        )
        if feedback:
            copy_task += "\nPrevious Direction Gate feedback:\n" + feedback
        copy_result = run_claude_agent("copy_director", context=base_context, task=copy_task)
        tracker.record_text(f"copy_direction:{group_id}:v{attempt + 1}", copy_result)
        try:
            check_copy_direction(copy_result.data)
        except QualityCheckError as exc:
            feedback = f"Copy deterministic validation failed: {exc}"
            continue

        art_context = dict(base_context)
        art_context["copy_direction"] = copy_result.data
        art_task = (
            "Generate at least two materially different art directions for the selected copy, "
            "compare them, select one, and preserve explicit copy-safe areas for all formats."
        )
        if feedback:
            art_task += "\nPrevious Direction Gate feedback:\n" + feedback
        art_result = run_claude_agent("art_director", context=art_context, task=art_task)
        tracker.record_text(f"art_direction:{group_id}:v{attempt + 1}", art_result)
        try:
            check_art_direction(art_result.data)
        except QualityCheckError as exc:
            feedback = f"Art deterministic validation failed: {exc}"
            continue

        prompt_context = dict(art_context)
        prompt_context["art_direction"] = art_result.data
        prompt_task = (
            "Translate the selected copy and selected art direction into a generation package. "
            "Do not change approved meaning. Put exact important Japanese text in overlay_text."
        )
        if feedback:
            prompt_task += "\nPrevious Direction Gate feedback:\n" + feedback
        prompt_result = run_claude_agent("prompt_designer", context=prompt_context, task=prompt_task)
        tracker.record_text(f"prompt_design:{group_id}:v{attempt + 1}", prompt_result)

        save_json(project_dir / "02_direction" / "copy" / f"{group_id}-v{attempt + 1:02d}.json", copy_result.data)
        save_json(project_dir / "02_direction" / "art" / f"{group_id}-v{attempt + 1:02d}.json", art_result.data)
        save_json(project_dir / "02_direction" / "prompts" / f"{group_id}-v{attempt + 1:02d}.json", prompt_result.data)

        gate_result = run_codex_gate(
            "direction_gate",
            original_request=original_request,
            upstream_outputs={
                "recruitment_analysis": recruitment,
                "production_plan": production_plan,
                "creative_group": creative_group,
                "copy_direction": copy_result.data,
                "art_direction": art_result.data,
                "prompt_package": prompt_result.data,
            },
        )
        tracker.record_text(f"codex_direction_gate:{group_id}:v{attempt + 1}", gate_result)
        gate = gate_result.data
        save_json(
            project_dir / "01_strategy" / "quality_gates" / f"direction-gate-{group_id}-v{attempt + 1:02d}.json",
            gate,
        )
        if gate.get("decision") == "pass":
            save_json(project_dir / "02_direction" / "copy" / f"{group_id}.json", copy_result.data)
            save_json(project_dir / "02_direction" / "art" / f"{group_id}.json", art_result.data)
            save_json(project_dir / "02_direction" / "prompts" / f"{group_id}.json", prompt_result.data)
            save_json(project_dir / "01_strategy" / "quality_gates" / f"direction-gate-{group_id}.json", gate)
            return {
                "copy_direction": copy_result.data,
                "art_direction": art_result.data,
                "prompt_package": prompt_result.data,
                "direction_gate": gate,
            }
        _handle_non_revision(gate.get("decision"), gate)
        feedback = _gate_feedback(gate)

    raise PipelineStop("needs_human_review", f"Direction Gate revision limit reached for {group_id}.")

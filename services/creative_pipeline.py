from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
import shutil
from typing import Any

import yaml

from services.image_generator import OpenAIImageGenerator, parse_dimensions
from services.image_review import review_image
from services.manifest import load_rows, write_rows
from services.overlay_renderer import render_overlay
from services.pipeline_stages import PipelineStop, run_direction_stage, save_json
from services.quality_gate import run_codex_gate
from services.usage_tracker import UsageTracker


REPO_ROOT = Path(__file__).resolve().parents[1]
QUALITY_CONFIG = REPO_ROOT / "configs" / "quality.yaml"


def load_quality_config() -> dict:
    return (yaml.safe_load(QUALITY_CONFIG.read_text(encoding="utf-8")) or {}).get("quality", {})


def _feedback(review: dict, final_gate: dict) -> tuple[str, set[str]]:
    lines = []
    codes: set[str] = set()
    for item in review.get("issues") or []:
        code = str(item.get("code") or "review_error")
        codes.add(code)
        lines.append(
            f"Reviewer/{code}: {item.get('description')} | revision={item.get('revision_instruction')}"
        )
    for item in final_gate.get("issues") or []:
        code = str(item.get("code") or "review_error")
        codes.add(code)
        lines.append(
            f"Codex/{code}: {item.get('description')} | return_to={item.get('return_to')}"
        )
    if not lines:
        lines.append(final_gate.get("next_action") or "Improve the creative to pass final QA.")
    return "\n".join(lines), codes


def _estimated_creative_cost(
    tracker: UsageTracker,
    shared_cost: float | None,
    creative_start_cost: float | None,
    quantity: int,
) -> float | None:
    current = tracker.total_estimated_cost_yen()
    if current is None or shared_cost is None or creative_start_cost is None:
        return None
    return round((shared_cost / quantity) + max(0.0, current - creative_start_cost), 2)


def produce_creatives(
    *,
    project_dir: Path,
    project: dict[str, Any],
    original_request: dict[str, Any],
    recruitment: dict,
    production_plan: dict,
    directions: dict[str, dict],
    tracker: UsageTracker,
) -> dict[str, dict]:
    quality = load_quality_config()
    reviewer_pass = float(quality.get("reviewer_pass_score", 90))
    final_pass = float(quality.get("final_gate_pass_score", 92))
    max_revisions = int(quality.get("max_revision_count", 3))
    budget = quality.get("budget") or {}
    stop_yen = float(budget.get("stop_and_escalate_yen_per_final_image", 400))
    revision_ceiling_yen = float(
        budget.get("do_not_start_another_revision_at_or_above_yen", 330)
    )

    manifest_path = project_dir / "creative-manifest.csv"
    rows = load_rows(manifest_path)
    if not rows:
        raise PipelineStop("blocked", "creative-manifest.csv has no creatives.")

    image_generator = OpenAIImageGenerator()
    shared_cost = tracker.total_estimated_cost_yen()
    quantity = len(rows)

    group_map = {
        group["creative_group_id"]: group
        for group in production_plan.get("creative_groups", [])
    }

    for row_index, row in enumerate(rows):
        creative_id = row["creative_id"]
        group_id = row["creative_group_id"]
        if group_id not in directions or group_id not in group_map:
            raise PipelineStop("blocked", f"Missing approved direction for {creative_id}/{group_id}.")

        creative_start_cost = tracker.total_estimated_cost_yen()
        revision_feedback = ""
        row["status"] = "generating"
        row["generation_status"] = "generating"
        write_rows(manifest_path, rows)

        for attempt in range(max_revisions + 1):
            version = attempt + 1
            row["version"] = str(version)
            row["revision_count"] = str(attempt)
            direction = directions[group_id]
            prompt_package = direction["prompt_package"]
            width, height = parse_dimensions(
                row.get("format", ""), row.get("width", ""), row.get("height", "")
            )

            batch_id = row.get("batch_id") or "B001"
            generated_dir = project_dir / "03_batches" / batch_id / creative_id / "generated"
            review_dir = project_dir / "03_batches" / batch_id / creative_id / "review"
            generated_dir.mkdir(parents=True, exist_ok=True)
            review_dir.mkdir(parents=True, exist_ok=True)

            background_path = generated_dir / f"v{version:02d}_background.png"
            final_path = generated_dir / f"v{version:02d}.png"
            prompt = str(prompt_package.get("prompt") or "").strip()
            prompt += (
                f"\n\nThis output is creative {creative_id}, variation {row_index + 1} of {quantity}. "
                f"Target final canvas is {width}x{height}. Preserve approved message and composition, "
                "but create a visually distinct execution from sibling creatives in the same group."
            )
            if revision_feedback:
                prompt += "\n\nREVISION REQUIREMENTS:\n" + revision_feedback

            image_generator.generate(
                prompt=prompt,
                width=width,
                height=height,
                output_path=background_path,
            )
            tracker.record_image(
                f"image_generation:{creative_id}:v{version}",
                provider="openai",
                model=image_generator.model,
                count=1,
            )

            overlay = prompt_package.get("overlay_text") or []
            if overlay:
                render_overlay(background_path, overlay, final_path)
            else:
                shutil.copy2(background_path, final_path)

            review_context = {
                "creative_id": creative_id,
                "manifest_row": row,
                "original_request": original_request,
                "recruitment_analysis": recruitment,
                "production_plan": production_plan,
                "creative_group": group_map[group_id],
                "copy_direction": direction["copy_direction"],
                "art_direction": direction["art_direction"],
                "prompt_package": prompt_package,
            }
            review_result = review_image(image_path=final_path, context=review_context)
            tracker.record_text(f"creative_review:{creative_id}:v{version}", review_result)
            review = review_result.data
            review_path = review_dir / f"claude-v{version:02d}.json"
            save_json(review_path, review)

            final_gate_result = run_codex_gate(
                "final_traceability_gate",
                original_request=original_request,
                upstream_outputs={**review_context, "creative_review": review},
                image_path=final_path,
            )
            tracker.record_text(f"codex_final_gate:{creative_id}:v{version}", final_gate_result)
            final_gate = final_gate_result.data
            codex_review_path = review_dir / f"codex-v{version:02d}.json"
            save_json(codex_review_path, final_gate)

            claude_score = float(review.get("total_score") or 0)
            codex_score = float(final_gate.get("score") or 0)
            passed = (
                review.get("decision") == "reviewer_pass"
                and claude_score >= reviewer_pass
                and final_gate.get("decision") == "pass"
                and codex_score >= final_pass
            )

            estimated_cost = _estimated_creative_cost(
                tracker, shared_cost, creative_start_cost, quantity
            )
            if estimated_cost is not None:
                row["cost_yen"] = f"{estimated_cost:.2f}"
                if estimated_cost >= stop_yen:
                    row["status"] = "needs_human_review"
                    row["review_status"] = "budget_guard"
                    row["updated_at"] = datetime.now().isoformat(timespec="seconds")
                    write_rows(manifest_path, rows)
                    raise PipelineStop(
                        "needs_human_review",
                        f"{creative_id} reached the hard cost ceiling: {estimated_cost:.2f} JPY",
                    )

            row["claude_score"] = f"{claude_score:.1f}"
            row["codex_score"] = f"{codex_score:.1f}"
            row["final_score"] = f"{min(claude_score, codex_score):.1f}"
            row["image_path"] = str(final_path)
            row["review_path"] = str(codex_review_path)
            row["generation_status"] = "generated"
            row["review_status"] = "pass" if passed else "revision"
            row["updated_at"] = datetime.now().isoformat(timespec="seconds")

            if passed:
                delivery_path = project_dir / "05_delivery" / f"{creative_id}.png"
                shutil.copy2(final_path, delivery_path)
                row["image_path"] = str(delivery_path)
                row["status"] = "completed"
                row["generation_status"] = "completed"
                row["review_status"] = "completed"
                write_rows(manifest_path, rows)
                break

            # Do not spend on another automatic revision once the current estimated
            # cost is already near the 400 JPY hard ceiling.
            if estimated_cost is not None and estimated_cost >= revision_ceiling_yen:
                row["status"] = "needs_human_review"
                row["review_status"] = "budget_revision_guard"
                row["updated_at"] = datetime.now().isoformat(timespec="seconds")
                write_rows(manifest_path, rows)
                raise PipelineStop(
                    "needs_human_review",
                    (
                        f"{creative_id} is not yet approved and costs {estimated_cost:.2f} JPY. "
                        f"Another automatic revision is blocked at {revision_ceiling_yen:.2f} JPY "
                        "to protect the 400 JPY/final-image ceiling."
                    ),
                )

            if attempt >= max_revisions:
                row["status"] = "needs_human_review"
                row["review_status"] = "revision_limit"
                write_rows(manifest_path, rows)
                raise PipelineStop(
                    "needs_human_review",
                    f"{creative_id} reached revision limit ({max_revisions}).",
                )

            revision_feedback, codes = _feedback(review, final_gate)
            upstream_codes = {"fact_error", "strategy_error", "missing_information"}
            if codes & upstream_codes:
                row["status"] = "needs_human_review"
                row["review_status"] = "upstream_error"
                write_rows(manifest_path, rows)
                decision = (
                    "needs_clarification"
                    if "missing_information" in codes
                    else "needs_human_review"
                )
                raise PipelineStop(
                    decision,
                    f"{creative_id} found upstream issue after generation: {revision_feedback}",
                )

            direction_codes = {"copy_error", "art_error", "prompt_error", "brand_error"}
            if codes & direction_codes:
                revised_request = deepcopy(original_request)
                revised_request["final_review_revision_feedback"] = revision_feedback
                directions[group_id] = run_direction_stage(
                    project_dir=project_dir,
                    original_request=revised_request,
                    recruitment=recruitment,
                    production_plan=production_plan,
                    creative_group=group_map[group_id],
                    tracker=tracker,
                    max_revisions=max_revisions,
                )

            row["status"] = "revision"
            row["generation_status"] = "revision"
            write_rows(manifest_path, rows)
        else:
            raise PipelineStop("needs_human_review", f"Unable to complete {creative_id}.")

    write_rows(manifest_path, rows)
    return directions

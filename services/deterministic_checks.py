from __future__ import annotations

from typing import Any


class QualityCheckError(ValueError):
    pass


def check_production_plan(plan: dict[str, Any], *, strategy_candidate_min: int = 5) -> None:
    requested = int(plan.get("requested_quantity") or 0)
    groups = plan.get("creative_groups") or []
    generated = sum(int(group.get("quantity") or 0) for group in groups)
    if requested != generated:
        raise QualityCheckError(
            f"Creative quantity mismatch: requested={requested}, planned={generated}"
        )

    candidates = plan.get("candidate_axes") or []
    if len(candidates) < strategy_candidate_min:
        raise QualityCheckError(
            f"Strategy competition requires at least {strategy_candidate_min} candidates; got {len(candidates)}"
        )

    selected = set(plan.get("selected_axes") or [])
    known = {item.get("axis_id") for item in candidates}
    unknown_selected = selected - known
    if unknown_selected:
        raise QualityCheckError(f"Unknown selected axis IDs: {sorted(unknown_selected)}")

    for group in groups:
        if not group.get("trace_to_facts"):
            raise QualityCheckError(
                f"Creative Group {group.get('creative_group_id')} has no fact traceability."
            )


def check_copy_direction(copy_direction: dict[str, Any], *, copy_candidate_min: int = 3) -> None:
    candidates = copy_direction.get("candidates") or []
    if len(candidates) < copy_candidate_min:
        raise QualityCheckError(
            f"Copy competition requires at least {copy_candidate_min} candidates; got {len(candidates)}"
        )
    ids = {item.get("copy_id") for item in candidates}
    if copy_direction.get("selected_copy") not in ids:
        raise QualityCheckError("selected_copy does not reference a candidate copy_id.")
    for candidate in candidates:
        if not candidate.get("trace_to_facts"):
            raise QualityCheckError(
                f"Copy {candidate.get('copy_id')} has no fact traceability."
            )


def check_art_direction(art_direction: dict[str, Any], *, art_candidate_min: int = 2) -> None:
    candidates = art_direction.get("candidates") or []
    if len(candidates) < art_candidate_min:
        raise QualityCheckError(
            f"Art competition requires at least {art_candidate_min} candidates; got {len(candidates)}"
        )
    ids = {item.get("art_id") for item in candidates}
    if art_direction.get("selected_art") not in ids:
        raise QualityCheckError("selected_art does not reference a candidate art_id.")


def check_revision_budget(revision_count: int, max_revision_count: int) -> None:
    if revision_count > max_revision_count:
        raise QualityCheckError(
            f"Revision limit exceeded: {revision_count} > {max_revision_count}"
        )


def check_cost_budget(cost_yen: float, stop_yen: float) -> None:
    if cost_yen >= stop_yen:
        raise QualityCheckError(
            f"Cost guard triggered: {cost_yen:.2f} JPY >= {stop_yen:.2f} JPY"
        )

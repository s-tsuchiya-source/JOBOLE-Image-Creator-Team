from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


MANIFEST_COLUMNS = [
    "project_id", "creative_group_id", "creative_id", "batch_id", "theme",
    "target", "message", "format", "width", "height", "copy_status",
    "art_status", "prompt_status", "generation_status", "review_status",
    "version", "claude_score", "codex_score", "final_score",
    "revision_count", "prompt_path", "image_path", "review_path", "cost_yen",
    "status", "updated_at",
]


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            normalized = {column: row.get(column, "") for column in MANIFEST_COLUMNS}
            writer.writerow(normalized)


def ensure_current_schema(path: Path, project_id: str) -> list[dict]:
    rows = load_rows(path)
    now = datetime.now().isoformat(timespec="seconds")
    upgraded = []
    for index, row in enumerate(rows, start=1):
        item = {column: row.get(column, "") for column in MANIFEST_COLUMNS}
        item["project_id"] = item["project_id"] or project_id
        item["creative_id"] = item["creative_id"] or f"CR{index:03d}"
        item["status"] = item["status"] or "pending"
        item["copy_status"] = item["copy_status"] or "pending"
        item["art_status"] = item["art_status"] or "pending"
        item["prompt_status"] = item["prompt_status"] or "pending"
        item["generation_status"] = item["generation_status"] or "pending"
        item["review_status"] = item["review_status"] or "pending"
        item["version"] = item["version"] or "0"
        item["revision_count"] = item["revision_count"] or "0"
        item["cost_yen"] = item["cost_yen"] or "0"
        item["updated_at"] = now
        upgraded.append(item)
    write_rows(path, upgraded)
    return upgraded


def apply_creative_plan(path: Path, project_id: str, plan: dict) -> list[dict]:
    existing = ensure_current_schema(path, project_id)
    quantity = int(plan.get("requested_quantity") or len(existing) or 1)
    rows: list[dict] = []
    index = 1
    now = datetime.now().isoformat(timespec="seconds")

    for group in plan.get("creative_groups", []):
        group_quantity = int(group.get("quantity") or 0)
        formats = group.get("formats") or [""]
        for local_index in range(group_quantity):
            format_value = formats[local_index % len(formats)] if formats else ""
            width, height = "", ""
            if "x" in format_value.lower():
                parts = format_value.lower().split("x", 1)
                if all(part.isdigit() for part in parts):
                    width, height = parts
            rows.append({
                "project_id": project_id,
                "creative_group_id": group.get("creative_group_id", ""),
                "creative_id": f"CR{index:03d}",
                "batch_id": f"B{((index - 1) // 10) + 1:03d}",
                "theme": group.get("theme", ""),
                "target": group.get("target", ""),
                "message": group.get("message", ""),
                "format": format_value,
                "width": width,
                "height": height,
                "copy_status": "pending",
                "art_status": "pending",
                "prompt_status": "pending",
                "generation_status": "pending",
                "review_status": "pending",
                "version": "0",
                "revision_count": "0",
                "cost_yen": "0",
                "status": "pending",
                "updated_at": now,
            })
            index += 1

    if len(rows) != quantity:
        raise ValueError(
            f"Creative Plan quantity mismatch: requested={quantity}, generated={len(rows)}"
        )
    write_rows(path, rows)
    return rows

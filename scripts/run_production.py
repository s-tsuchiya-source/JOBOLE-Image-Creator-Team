from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sys

import yaml
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from input_loader import normalize_project_inputs
from load_project import load_environment, load_yaml, resolve_project_dir
from services.agent_runner import load_agent_config
from services.contact_sheet import build_contact_sheet
from services.creative_pipeline import produce_creatives
from services.image_generator import check_image_backend
from services.manifest import apply_creative_plan, ensure_current_schema, load_rows
from services.pipeline_stages import (
    PipelineStop,
    run_direction_stage,
    run_recruitment_stage,
    run_strategy_stage,
    save_json,
)
from services.schema_validator import load_schema
from services.usage_tracker import UsageTracker


load_dotenv(REPO_ROOT / ".env")
QUALITY_CONFIG = REPO_ROOT / "configs" / "quality.yaml"


def save_project_yaml(path: Path, project: dict) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False)


def set_project_status(project_dir: Path, project: dict, status: str) -> None:
    project["status"] = status
    project["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_project_yaml(project_dir / "project.yaml", project)


def load_quality() -> dict:
    return (yaml.safe_load(QUALITY_CONFIG.read_text(encoding="utf-8")) or {}).get("quality", {})


def preflight(project_dir: Path, project: dict, intake: dict) -> dict:
    checks = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    add("project_yaml", bool(project), str(project_dir / "project.yaml"))
    add("job_posting", intake["job_posting_count"] > 0, f"count={intake['job_posting_count']}")
    add("hearing_optional", True, f"provided={intake.get('hearing_provided', False)}")
    add("input_errors", not intake["errors"], "; ".join(intake["errors"]) or "none")

    for agent_name in (
        "recruitment_analyst",
        "production_director",
        "copy_director",
        "art_director",
        "prompt_designer",
        "creative_reviewer",
    ):
        try:
            config = load_agent_config(agent_name)
            load_schema(config["schema"])
            role_path = REPO_ROOT / config["file"]
            add(f"agent:{agent_name}", role_path.exists(), str(role_path))
        except Exception as exc:
            add(f"agent:{agent_name}", False, str(exc))

    try:
        load_schema("schemas/quality-gate.schema.json")
        add("quality_gate_schema", True, "schemas/quality-gate.schema.json")
    except Exception as exc:
        add("quality_gate_schema", False, str(exc))

    add(
        "codex_cco_role",
        (REPO_ROOT / ".codex" / "chief-creative-officer.md").exists(),
        ".codex/chief-creative-officer.md",
    )
    add("quality_config", QUALITY_CONFIG.exists(), str(QUALITY_CONFIG))

    mode = os.getenv("PRODUCTION_MODE", "dry-run").strip().lower()
    if mode == "live":
        claude_command = os.getenv("CLAUDE_CLI_COMMAND", "claude")
        codex_command = os.getenv("CODEX_CLI_COMMAND", "codex")
        claude_path = shutil.which(claude_command)
        codex_path = shutil.which(codex_command)
        add("claude_code_cli", bool(claude_path), claude_path or f"missing: {claude_command}")
        add("codex_cli", bool(codex_path), codex_path or f"missing: {codex_command}")

        backend = os.getenv("IMAGE_BACKEND", "local_webui").strip().lower()
        if backend in {"local", "local_webui", "webui", "forge", "automatic1111"}:
            try:
                info = check_image_backend()
                add("image_backend", bool(info.get("ok")), json.dumps(info, ensure_ascii=False))
            except Exception as exc:
                add("image_backend", False, f"local WebUI unavailable: {exc}")
        elif backend in {"openai", "openai_api"}:
            required = {
                "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
                "OPENAI_IMAGE_MODEL": os.getenv("OPENAI_IMAGE_MODEL"),
                "USDJPY_RATE": os.getenv("USDJPY_RATE"),
                "OPENAI_IMAGE_ESTIMATED_USD_PER_GENERATION": os.getenv(
                    "OPENAI_IMAGE_ESTIMATED_USD_PER_GENERATION"
                ),
            }
            for name, value in required.items():
                add(
                    f"image_setting:{name.lower()}",
                    bool((value or "").strip()),
                    "configured" if (value or "").strip() else "missing",
                )
        else:
            add("image_backend", False, f"unsupported IMAGE_BACKEND={backend!r}")

    return {
        "mode": mode,
        "text_ai": "claude_code_subscription + codex_chatgpt_login",
        "image_backend": os.getenv("IMAGE_BACKEND", "local_webui"),
        "ready": all(check["passed"] for check in checks),
        "checks": checks,
    }


def build_original_request(project: dict, intake: dict) -> dict:
    source_bundle = Path(intake["source_bundle"]).read_text(encoding="utf-8-sig")
    source_index = Path(intake["source_index"]).read_text(encoding="utf-8-sig")
    return {
        "project": project,
        "source_bundle": source_bundle,
        "source_index": json.loads(source_index),
        "reference_count": intake["reference_count"],
        "hearing_provided": intake["hearing_provided"],
    }


def write_production_summary(
    project_dir: Path,
    project: dict,
    tracker: UsageTracker,
    contact_sheet: Path | None = None,
) -> None:
    rows = load_rows(project_dir / "creative-manifest.csv")
    statuses: dict[str, int] = {}
    for row in rows:
        status = row.get("status") or "unknown"
        statuses[status] = statuses.get(status, 0) + 1
    summary = {
        "project_id": project.get("project_id"),
        "status": project.get("status"),
        "human_approval_status": project.get("human_approval_status"),
        "creative_count": len(rows),
        "creative_statuses": statuses,
        "estimated_incremental_api_cost_yen": tracker.total_estimated_cost_yen(),
        "text_ai_billing": "subscription_login",
        "image_backend": os.getenv("IMAGE_BACKEND", "local_webui"),
        "delivery_dir": str(project_dir / "05_delivery"),
        "contact_sheet": str(contact_sheet) if contact_sheet else None,
        "completed_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_json(project_dir / "04_project_review" / "production-summary.json", summary)


def execute_live(project_dir: Path, project: dict, intake: dict) -> None:
    quality = load_quality()
    max_revisions = int(quality.get("max_revision_count", 3))
    tracker = UsageTracker(project_dir)
    original_request = build_original_request(project, intake)

    try:
        set_project_status(project_dir, project, "analyzing")
        recruitment, fact_gate = run_recruitment_stage(
            project_dir=project_dir,
            original_request=original_request,
            tracker=tracker,
            max_revisions=max_revisions,
        )

        set_project_status(project_dir, project, "planning")
        production_plan, strategy_gate = run_strategy_stage(
            project_dir=project_dir,
            original_request=original_request,
            recruitment=recruitment,
            fact_gate=fact_gate,
            requested_quantity=int(project.get("quantity") or 1),
            tracker=tracker,
            max_revisions=max_revisions,
        )
        if production_plan.get("status") != "ready_for_direction":
            decision = production_plan.get("status") or "needs_clarification"
            raise PipelineStop(decision, f"Production plan status: {decision}")

        apply_creative_plan(
            project_dir / "creative-manifest.csv",
            project["project_id"],
            production_plan,
        )

        set_project_status(project_dir, project, "directing")
        directions: dict[str, dict] = {}
        for group in production_plan.get("creative_groups", []):
            group_id = group["creative_group_id"]
            directions[group_id] = run_direction_stage(
                project_dir=project_dir,
                original_request=original_request,
                recruitment=recruitment,
                production_plan=production_plan,
                creative_group=group,
                tracker=tracker,
                max_revisions=max_revisions,
            )

        direction_index = {
            group_id: {
                "copy": f"02_direction/copy/{group_id}.json",
                "art": f"02_direction/art/{group_id}.json",
                "prompt": f"02_direction/prompts/{group_id}.json",
                "gate": f"01_strategy/quality_gates/direction-gate-{group_id}.json",
            }
            for group_id in directions
        }
        save_json(project_dir / "02_direction" / "direction-summary.json", direction_index)

        set_project_status(project_dir, project, "generating")
        produce_creatives(
            project_dir=project_dir,
            project=project,
            original_request=original_request,
            recruitment=recruitment,
            production_plan=production_plan,
            directions=directions,
            tracker=tracker,
        )

        set_project_status(project_dir, project, "completed")
        project["human_approval_status"] = "pending"
        project["estimated_incremental_api_cost_yen"] = tracker.total_estimated_cost_yen()
        project["text_ai_billing"] = "subscription_login"
        project["image_backend"] = os.getenv("IMAGE_BACKEND", "local_webui")
        save_project_yaml(project_dir / "project.yaml", project)
        contact_sheet = build_contact_sheet(project_dir)
        write_production_summary(project_dir, project, tracker, contact_sheet)

        print("Production completed successfully.")
        print(f"Project: {project.get('project_id')}")
        print(f"Image backend: {os.getenv('IMAGE_BACKEND', 'local_webui')}")
        print(f"Incremental API cost estimate: {tracker.total_estimated_cost_yen()} JPY")
        print(f"Delivery candidates: {project_dir / '05_delivery'}")
        if contact_sheet:
            print(f"Contact sheet: {contact_sheet}")
        print("Human final approval: pending")

    except PipelineStop as exc:
        status_map = {
            "needs_clarification": "needs_clarification",
            "needs_human_review": "needs_human_review",
            "blocked": "blocked",
            "revise": "revision",
        }
        set_project_status(project_dir, project, status_map.get(exc.decision, exc.decision))
        project["stop_reason"] = exc.detail
        save_project_yaml(project_dir / "project.yaml", project)
        write_production_summary(project_dir, project, tracker)
        raise SystemExit(f"Production stopped: {exc.decision} - {exc.detail}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run Codex CCO (ChatGPT login) + Claude Code specialists + selected image backend."
        )
    )
    parser.add_argument("project_id", help="PJ-0001 or project folder prefix")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate project and AI-team structure without running AI/image generation.",
    )
    args = parser.parse_args()

    projects_root = load_environment()
    project_dir = resolve_project_dir(projects_root, args.project_id)
    project = load_yaml(project_dir / "project.yaml")
    ensure_current_schema(
        project_dir / "creative-manifest.csv",
        project.get("project_id", args.project_id),
    )
    intake = normalize_project_inputs(project_dir)

    report = preflight(project_dir, project, intake)
    report_path = project_dir / "04_project_review" / "preflight-report.json"
    save_json(report_path, report)

    if args.dry_run or report["mode"] != "live":
        print(f"Preflight: {'PASS' if report['ready'] else 'FAIL'}")
        for check in report["checks"]:
            mark = "OK" if check["passed"] else "NG"
            print(f"[{mark}] {check['name']}: {check['detail']}")
        print(f"Report: {report_path}")
        if not report["ready"]:
            raise SystemExit(2)
        print("dry-run completed. No Claude/Codex/image generation was executed.")
        return

    if not report["ready"]:
        raise SystemExit("Preflight failed. See preflight-report.json")
    execute_live(project_dir, project, intake)


if __name__ == "__main__":
    main()

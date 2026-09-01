from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
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
from services.agent_runner import load_agent_config, run_claude_agent
from services.manifest import apply_creative_plan, ensure_current_schema
from services.quality_gate import run_codex_gate
from services.schema_validator import load_schema


load_dotenv(REPO_ROOT / ".env")


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )


def save_project_yaml(path: Path, project: dict) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False)


def set_project_status(project_dir: Path, project: dict, status: str) -> None:
    project["status"] = status
    save_project_yaml(project_dir / "project.yaml", project)


def preflight(project_dir: Path, project: dict, intake: dict) -> dict:
    checks = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    add("project_yaml", bool(project), str(project_dir / "project.yaml"))
    add("job_posting", intake["job_posting_count"] > 0, f"count={intake['job_posting_count']}")
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

    mode = os.getenv("PRODUCTION_MODE", "dry-run").lower()
    if mode == "live":
        add("anthropic_api_key", bool(os.getenv("ANTHROPIC_API_KEY")), "configured" if os.getenv("ANTHROPIC_API_KEY") else "missing")
        add("anthropic_model", bool(os.getenv("ANTHROPIC_MODEL")), os.getenv("ANTHROPIC_MODEL") or "missing")
        add("openai_api_key", bool(os.getenv("OPENAI_API_KEY")), "configured" if os.getenv("OPENAI_API_KEY") else "missing")
        add("openai_cco_model", bool(os.getenv("OPENAI_CCO_MODEL")), os.getenv("OPENAI_CCO_MODEL") or "missing")

    return {
        "mode": mode,
        "ready": all(check["passed"] for check in checks),
        "checks": checks,
    }


def require_gate_pass(gate_result: dict, project_dir: Path, project: dict) -> None:
    decision = gate_result.get("decision")
    if decision == "pass":
        return
    status_map = {
        "needs_clarification": "needs_clarification",
        "needs_human_review": "needs_human_review",
        "blocked": "blocked",
        "revise": "revision",
    }
    set_project_status(project_dir, project, status_map.get(decision, "revision"))
    raise SystemExit(f"Quality Gate stopped production: {decision}")


def execute_live(project_dir: Path, project: dict, intake: dict) -> None:
    source_bundle = Path(intake["source_bundle"]).read_text(encoding="utf-8-sig")
    original_request = {
        "project": project,
        "source_bundle": source_bundle,
        "reference_count": intake["reference_count"],
        "hearing_provided": intake["hearing_provided"],
    }

    set_project_status(project_dir, project, "analyzing")

    recruitment = run_claude_agent(
        "recruitment_analyst",
        context=original_request,
        task="Extract recruitment facts with evidence. Do not create copy or visual ideas.",
    )
    recruitment_path = project_dir / "01_strategy" / "recruitment" / "recruitment-analysis.json"
    save_json(recruitment_path, recruitment.data)

    fact_gate = run_codex_gate(
        "fact_gate",
        original_request=original_request,
        upstream_outputs={"recruitment_analysis": recruitment.data},
    )
    save_json(project_dir / "01_strategy" / "quality_gates" / "fact-gate.json", fact_gate.data)
    require_gate_pass(fact_gate.data, project_dir, project)

    set_project_status(project_dir, project, "planning")
    strategy_context = {
        "original_request": original_request,
        "recruitment_analysis": recruitment.data,
        "fact_gate": fact_gate.data,
        "requested_quantity": project.get("quantity"),
    }
    production = run_claude_agent(
        "production_director",
        context=strategy_context,
        task=(
            "Create a competition-based production plan. Candidate axes must be compared; "
            "creative group quantities must sum exactly to requested_quantity."
        ),
    )
    production_path = project_dir / "01_strategy" / "production-plan.json"
    save_json(production_path, production.data)

    strategy_gate = run_codex_gate(
        "strategy_gate",
        original_request=original_request,
        upstream_outputs={
            "recruitment_analysis": recruitment.data,
            "fact_gate": fact_gate.data,
            "production_plan": production.data,
        },
    )
    save_json(project_dir / "01_strategy" / "quality_gates" / "strategy-gate.json", strategy_gate.data)
    require_gate_pass(strategy_gate.data, project_dir, project)

    if production.data.get("status") != "ready_for_direction":
        target_status = production.data.get("status") or "needs_clarification"
        set_project_status(project_dir, project, target_status)
        raise SystemExit(f"Production plan is not ready: {target_status}")

    manifest_path = project_dir / "creative-manifest.csv"
    apply_creative_plan(manifest_path, project["project_id"], production.data)
    set_project_status(project_dir, project, "directing")

    direction_summary = {}
    for group in production.data.get("creative_groups", []):
        group_id = group["creative_group_id"]
        group_context = {
            "original_request": original_request,
            "recruitment_analysis": recruitment.data,
            "production_plan": production.data,
            "creative_group": group,
        }

        copy_result = run_claude_agent(
            "copy_director",
            context=group_context,
            task="Generate multiple copy candidates, select one, and trace every claim to facts.",
        )
        copy_path = project_dir / "02_direction" / "copy" / f"{group_id}.json"
        save_json(copy_path, copy_result.data)

        art_context = dict(group_context)
        art_context["copy_direction"] = copy_result.data
        art_result = run_claude_agent(
            "art_director",
            context=art_context,
            task="Create art direction for the selected copy with explicit safe area and size variations.",
        )
        art_path = project_dir / "02_direction" / "art" / f"{group_id}.json"
        save_json(art_path, art_result.data)

        direction_gate = run_codex_gate(
            "direction_gate",
            original_request=original_request,
            upstream_outputs={
                "recruitment_analysis": recruitment.data,
                "production_plan": production.data,
                "creative_group": group,
                "copy_direction": copy_result.data,
                "art_direction": art_result.data,
            },
        )
        gate_path = project_dir / "01_strategy" / "quality_gates" / f"direction-gate-{group_id}.json"
        save_json(gate_path, direction_gate.data)
        require_gate_pass(direction_gate.data, project_dir, project)

        prompt_context = dict(art_context)
        prompt_context["art_direction"] = art_result.data
        prompt_context["direction_gate"] = direction_gate.data
        prompt_result = run_claude_agent(
            "prompt_designer",
            context=prompt_context,
            task=(
                "Translate approved directions into an image-generation prompt package. "
                "Keep exact job facts and important text in overlay_text."
            ),
        )
        prompt_path = project_dir / "02_direction" / "prompts" / f"{group_id}.json"
        save_json(prompt_path, prompt_result.data)
        direction_summary[group_id] = {
            "copy_path": str(copy_path),
            "art_path": str(art_path),
            "prompt_path": str(prompt_path),
        }

    save_json(project_dir / "02_direction" / "direction-summary.json", direction_summary)
    set_project_status(project_dir, project, "ready_for_image_generation")
    print("AI strategy/direction pipeline completed.")
    print("Status: ready_for_image_generation")
    print("Next implementation: image generation + image review + final traceability gate.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id", help="PJ-0001 or project folder prefix")
    parser.add_argument("--dry-run", action="store_true", help="Validate system without API calls")
    args = parser.parse_args()

    projects_root = load_environment()
    project_dir = resolve_project_dir(projects_root, args.project_id)
    project = load_yaml(project_dir / "project.yaml")
    ensure_current_schema(project_dir / "creative-manifest.csv", project.get("project_id", args.project_id))
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
        print("dry-run completed. No AI API calls were made.")
        return

    if not report["ready"]:
        raise SystemExit("Preflight failed. See preflight-report.json")
    execute_live(project_dir, project, intake)


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml

from input_loader import normalize_project_inputs
from load_project import (
    TMP_ROOT,
    load_environment,
    load_yaml,
    resolve_project_dir,
)


def ensure_intake_structure(project_dir: Path) -> None:
    for subdir in [
        "00_request/inbox/job_posting",
        "00_request/inbox/hearing",
        "00_request/inbox/references",
        "00_request/normalized",
        "01_strategy/recruitment",
        "01_strategy/quality_gates",
        "02_direction/copy",
        "02_direction/art",
        "02_direction/prompts",
        "03_batches",
        "04_project_review/claude",
        "04_project_review/codex",
        "05_delivery",
    ]:
        (project_dir / subdir).mkdir(parents=True, exist_ok=True)


def save_project_yaml(path: Path, project: dict) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(
            project,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )


def build_intake_task(project_dir: Path, project: dict, intake: dict) -> str:
    return f"""# Intake Task

## 対象案件
- project_id: {project.get('project_id', '')}
- project_name: {project.get('project_name', '')}
- client_name: {project.get('client_name', '')}
- objective: {project.get('objective', '')}
- requested_quantity: {project.get('quantity', '')}
- deadline: {project.get('deadline', '')}

## 入力ソース
- source_bundle: {intake['source_bundle']}
- source_index: {intake['source_index']}
- job_posting_count: {intake['job_posting_count']}
- hearing_count: {intake['hearing_count']} (optional)
- reference_count: {intake['reference_count']} (optional)

## 次工程
1. Claude Code Recruitment Analyst が求人事実を抽出する。
2. Codex CCO Fact Gate が検証する。
3. Claude Code Production Director が制作戦略を設計する。
4. 以降は `scripts/run_production.py` の品質パイプラインへ進む。

## 判定
求人原稿が1件以上正常に読み込めれば入力ゲートは通過可能。
ヒアリングがないことだけを理由に停止しない。
制作に不可欠な情報が不足する場合のみ、後続Agent/Gateが `needs_clarification` を返す。

## 保存先
- Strategy: {project_dir / '01_strategy'}
- Direction: {project_dir / '02_direction'}
- Review: {project_dir / '04_project_review'}
- Delivery: {project_dir / '05_delivery'}
"""


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/start_production.py <project_id_or_folder_name>")

    projects_root = load_environment()
    project_dir = resolve_project_dir(projects_root, sys.argv[1])
    ensure_intake_structure(project_dir)

    project_path = project_dir / "project.yaml"
    project = load_yaml(project_path)
    intake = normalize_project_inputs(project_dir)

    project["input_status"] = "ready" if intake["ready"] else "needs_input"
    project["status"] = "input_ready" if intake["ready"] else "awaiting_input"
    project["source_bundle"] = intake["source_bundle"]
    project["source_index"] = intake["source_index"]
    save_project_yaml(project_path, project)

    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = TMP_ROOT / "intake-report.json"
    report_path.write_text(
        json.dumps(intake, ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )

    task_path = TMP_ROOT / "intake-task.md"
    task_path.write_text(
        build_intake_task(project_dir, project, intake),
        encoding="utf-8-sig",
    )

    print(f"案件入力を解析しました: {project_dir.name}")
    print(f"求人原稿: {intake['job_posting_count']}件")
    print(f"ヒアリング: {intake['hearing_count']}件（任意）")
    print(f"参考素材: {intake['reference_count']}件（任意）")

    if intake["errors"]:
        print("入力エラー:")
        for error in intake["errors"]:
            print(f"- {error}")

    if not intake["ready"]:
        print("状態: needs_input")
        if intake["job_posting_count"] == 0:
            print("- 00_request/inbox/job_posting/ に求人原稿を配置してください。")
        raise SystemExit(2)

    print("状態: input_ready")
    print(f"Source Bundle: {intake['source_bundle']}")
    print(f"Intake Task: {task_path}")
    print("次工程: scripts/run_production.py でClaude/Codex品質パイプラインを実行します。")


if __name__ == "__main__":
    main()

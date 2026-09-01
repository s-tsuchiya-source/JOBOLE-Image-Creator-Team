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
        "01_strategy",
        "02_direction/text",
        "02_direction/image",
        "03_batches",
        "04_project_review",
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


def build_director_task(project_dir: Path, project: dict, intake: dict) -> str:
    return f"""# Production Director Task

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
- hearing_count: {intake['hearing_count']}
- reference_count: {intake['reference_count']}

## Production Directorが行うこと
1. `source-bundle.md` を最初から最後まで読む。
2. 求人原稿の事実情報とヒアリング上の要望を分離して整理する。
3. 推測で補ってはいけない項目を明示する。
4. ターゲット、採用上の魅力、訴求優先度、画像の目的を整理する。
5. 要求枚数に対して、どの訴求軸を何枚作るか制作計画を決める。
6. Text Director と Image Director に渡せる粒度まで具体化する。
7. 次の2ファイルをGoogle Drive側へ作成する。
   - `{project_dir / '01_strategy' / 'production-brief.md'}`
   - `{project_dir / '01_strategy' / 'creative-plan.yaml'}`

## production-brief.md 必須項目
- 求人/案件概要
- 採用ターゲット
- 応募者に伝えるべき魅力
- 訴求優先順位
- ヒアリング要望
- 必須表現
- 禁止/避ける表現
- ブランド/トーン
- 不足情報
- 制作方針

## creative-plan.yaml 必須項目
- total_creatives
- creative_groups
- 各groupの theme / target / message / quantity / formats
- assumptions
- missing_information

## 判定
不足情報が制作を止めるレベルなら `needs_clarification` とし、勝手に制作へ進めない。
制作可能なら `ready_for_direction` とする。
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

    task_path = TMP_ROOT / "production-director-task.md"
    task_path.write_text(
        build_director_task(project_dir, project, intake),
        encoding="utf-8-sig",
    )

    print(f"案件入力を解析しました: {project_dir.name}")
    print(f"求人原稿: {intake['job_posting_count']}件")
    print(f"ヒアリング: {intake['hearing_count']}件")
    print(f"参考素材: {intake['reference_count']}件")

    if intake["errors"]:
        print("入力エラー:")
        for error in intake["errors"]:
            print(f"- {error}")

    if not intake["ready"]:
        print("状態: needs_input")
        if intake["job_posting_count"] == 0:
            print("- 00_request/inbox/job_posting/ に求人原稿を配置してください。")
        if intake["hearing_count"] == 0:
            print("- 00_request/inbox/hearing/ にヒアリング資料を配置してください。")
        raise SystemExit(2)

    print("状態: input_ready")
    print(f"Source Bundle: {intake['source_bundle']}")
    print(f"Director Task: {task_path}")
    print("次工程: Production Director がDirector Taskを実行します。")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from datetime import date
import os
from pathlib import Path
import shutil
import sys

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
load_dotenv(REPO_ROOT / ".env")

from new_project import (
    create_manifest,
    ensure_project_structure,
    next_project_id,
    sanitize_name,
    write_project_yaml,
)


def _copy_files(paths: list[str] | None, destination: Path) -> list[str]:
    copied: list[str] = []
    for raw in paths or []:
        source = Path(raw).expanduser().resolve()
        if not source.exists() or not source.is_file():
            raise SystemExit(f"入力ファイルが見つかりません: {source}")
        target = destination / source.name
        counter = 2
        while target.exists() and target.read_bytes() != source.read_bytes():
            target = destination / f"{source.stem}_{counter}{source.suffix}"
            counter += 1
        if not target.exists():
            shutil.copy2(source, target)
        copied.append(str(target))
    return copied


def _read_optional_text(value: str | None, file_value: str | None) -> str:
    parts: list[str] = []
    if value and value.strip():
        parts.append(value.strip())
    if file_value:
        path = Path(file_value).expanduser().resolve()
        if not path.exists():
            raise SystemExit(f"テキストファイルが見つかりません: {path}")
        parts.append(path.read_text(encoding="utf-8-sig").strip())
    return "\n\n".join(part for part in parts if part)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a Google Drive project non-interactively from Codex/VSCode intake."
    )
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--client-name", default="")
    parser.add_argument("--objective", default="画像制作")
    parser.add_argument("--deadline", default="")
    parser.add_argument("--quantity", type=int, default=1)
    parser.add_argument("--job-posting", action="append", default=[])
    parser.add_argument("--hearing", action="append", default=[])
    parser.add_argument("--reference", action="append", default=[])
    parser.add_argument("--request-text", default="")
    parser.add_argument("--request-text-file", default="")
    parser.add_argument(
        "--job-posting-text-file",
        default="",
        help="Use when the job posting arrived as text rather than a normal attachment.",
    )
    args = parser.parse_args()

    if not 1 <= args.quantity <= 100:
        raise SystemExit("--quantity は1〜100で指定してください。")

    projects_root_value = os.getenv("PROJECTS_ROOT")
    if not projects_root_value:
        raise SystemExit("PROJECTS_ROOT が .env に設定されていません。")
    projects_root = Path(projects_root_value)
    projects_root.mkdir(parents=True, exist_ok=True)

    project_id = next_project_id(projects_root)
    slug = sanitize_name(args.client_name or args.project_name or "project") or "project"
    project_dir = projects_root / f"{project_id}_{slug}"
    ensure_project_structure(project_dir)

    job_dir = project_dir / "00_request" / "inbox" / "job_posting"
    hearing_dir = project_dir / "00_request" / "inbox" / "hearing"
    reference_dir = project_dir / "00_request" / "inbox" / "references"

    job_files = _copy_files(args.job_posting, job_dir)
    hearing_files = _copy_files(args.hearing, hearing_dir)
    reference_files = _copy_files(args.reference, reference_dir)

    if args.job_posting_text_file:
        source = Path(args.job_posting_text_file).expanduser().resolve()
        if not source.exists():
            raise SystemExit(f"求人原稿テキストが見つかりません: {source}")
        target = job_dir / "job-posting-from-text.md"
        target.write_text(source.read_text(encoding="utf-8-sig"), encoding="utf-8-sig")
        job_files.append(str(target))

    request_text = _read_optional_text(args.request_text, args.request_text_file)
    if request_text:
        target = hearing_dir / "request-text.md"
        target.write_text(
            "# Codex / VSCode Request Text\n\n" + request_text + "\n",
            encoding="utf-8-sig",
        )
        hearing_files.append(str(target))

    if not job_files:
        raise SystemExit(
            "求人原稿がありません。--job-posting または --job-posting-text-file が最低1つ必要です。"
        )

    project_data = {
        "project_id": project_id,
        "project_name": args.project_name,
        "client_name": args.client_name,
        "objective": args.objective,
        "deadline": args.deadline,
        "quantity": args.quantity,
        "created_at": date.today().isoformat(),
        "status": "awaiting_input",
        "input_status": "not_checked",
        "quality_mode": "quality_first",
        "human_final_approval_required": True,
        "intake_channel": "vscode_codex",
        "intake": {
            "job_postings": job_files,
            "hearings": hearing_files,
            "references": reference_files,
            "request_text_provided": bool(request_text),
        },
    }
    write_project_yaml(project_dir / "project.yaml", project_data)
    create_manifest(project_dir / "creative-manifest.csv", project_id, args.quantity)

    print(f"PROJECT_ID={project_id}")
    print(f"PROJECT_DIR={project_dir}")
    print(f"JOB_POSTINGS={len(job_files)}")
    print(f"HEARING_INPUTS={len(hearing_files)}")
    print(f"REFERENCES={len(reference_files)}")
    print("NEXT=python scripts/run_production.py " + project_id + " --dry-run")


if __name__ == "__main__":
    main()

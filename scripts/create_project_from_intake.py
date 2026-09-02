from __future__ import annotations

import argparse
import csv
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
load_dotenv(REPO_ROOT / ".env", override=True)

from new_project import (
    create_manifest,
    ensure_project_structure,
    next_project_id,
    sanitize_name,
    write_project_yaml,
)


def _copy_files(paths: list[str] | None, destination: Path) -> list[str]:
    destination.mkdir(parents=True, exist_ok=True)
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


def _derive_project_name(explicit: str, job_paths: list[str], job_text_file: str) -> str:
    if explicit.strip():
        return explicit.strip()
    if job_paths:
        return Path(job_paths[0]).stem
    if job_text_file:
        return Path(job_text_file).stem
    return "job-creative"


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return [
                    {str(k): "" if v is None else str(v).strip() for k, v in row.items()}
                    for row in csv.DictReader(handle)
                ]
        except UnicodeDecodeError:
            continue
    return []


def _infer_quantity_from_hearing(paths: list[str]) -> tuple[int | None, str]:
    for raw in paths:
        path = Path(raw).expanduser().resolve()
        if path.suffix.lower() != ".csv" or not path.exists():
            continue
        for row in _read_csv_rows(path):
            raw_quantity = row.get("制作枚数", "").strip()
            if not raw_quantity:
                continue
            digits = "".join(char for char in raw_quantity if char.isdigit())
            if digits:
                value = int(digits)
                if 1 <= value <= 100:
                    return value, f"hearing:{path.name}:制作枚数"
    return None, ""


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create a Phase 1 project from the minimum user intake: "
            "job file required, hearing/text optional."
        )
    )
    parser.add_argument("--project-name", default="")
    parser.add_argument("--client-name", default="")
    parser.add_argument("--objective", default="求人広告画像制作")
    parser.add_argument("--deadline", default="")
    parser.add_argument(
        "--quantity",
        type=int,
        default=0,
        help="Optional explicit override. If omitted, infer 制作枚数 from hearing CSV, otherwise default to 1.",
    )
    parser.add_argument(
        "--job-posting",
        action="append",
        default=[],
        help="Required. May be repeated for multiple job files.",
    )
    parser.add_argument(
        "--hearing",
        action="append",
        default=[],
        help="Optional hearing sheet/file.",
    )
    parser.add_argument(
        "--request-text",
        default="",
        help="Optional supplementary instruction text from the user.",
    )
    parser.add_argument(
        "--request-text-file",
        default="",
        help="Optional supplementary text stored in a UTF-8 text file.",
    )
    parser.add_argument(
        "--job-posting-text-file",
        default="",
        help="Internal fallback when a job posting arrived as pasted text rather than an attachment.",
    )
    args = parser.parse_args()

    if args.quantity < 0 or args.quantity > 100:
        raise SystemExit("--quantity は1〜100で指定してください。省略時は0のままで構いません。")

    if not args.job_posting and not args.job_posting_text_file:
        raise SystemExit(
            "求人ファイルがありません。--job-posting が最低1つ必要です。"
        )

    inferred_quantity, inferred_source = _infer_quantity_from_hearing(args.hearing)
    if args.quantity:
        quantity = args.quantity
        quantity_source = "explicit_argument"
    elif inferred_quantity:
        quantity = inferred_quantity
        quantity_source = inferred_source
    else:
        quantity = 1
        quantity_source = "phase1_default"

    projects_root_value = os.getenv("PROJECTS_ROOT")
    if not projects_root_value:
        raise SystemExit("PROJECTS_ROOT が .env に設定されていません。")
    projects_root = Path(projects_root_value)
    projects_root.mkdir(parents=True, exist_ok=True)

    project_name = _derive_project_name(
        args.project_name,
        args.job_posting,
        args.job_posting_text_file,
    )
    project_id = next_project_id(projects_root)
    slug = sanitize_name(args.client_name or project_name or "project") or "project"
    project_dir = projects_root / f"{project_id}_{slug}"
    ensure_project_structure(project_dir)

    job_dir = project_dir / "00_request" / "inbox" / "job_posting"
    hearing_dir = project_dir / "00_request" / "inbox" / "hearing"
    request_text_dir = project_dir / "00_request" / "inbox" / "request_text"

    job_files = _copy_files(args.job_posting, job_dir)
    hearing_files = _copy_files(args.hearing, hearing_dir)
    request_text_dir.mkdir(parents=True, exist_ok=True)

    if args.job_posting_text_file:
        source = Path(args.job_posting_text_file).expanduser().resolve()
        if not source.exists():
            raise SystemExit(f"求人原稿テキストが見つかりません: {source}")
        target = job_dir / "job-posting-from-text.md"
        target.write_text(source.read_text(encoding="utf-8-sig"), encoding="utf-8-sig")
        job_files.append(str(target))

    request_text = _read_optional_text(args.request_text, args.request_text_file)
    request_text_files: list[str] = []
    if request_text:
        target = request_text_dir / "request-text.md"
        target.write_text(
            "# Supplementary Request Text\n\n" + request_text + "\n",
            encoding="utf-8-sig",
        )
        request_text_files.append(str(target))

    project_data = {
        "project_id": project_id,
        "project_name": project_name,
        "client_name": args.client_name,
        "objective": args.objective,
        "deadline": args.deadline,
        "quantity": quantity,
        "quantity_source": quantity_source,
        "created_at": date.today().isoformat(),
        "status": "input_ready",
        "quality_mode": "phase1_benchmark_quality_v2",
        "human_final_approval_required": True,
        "intake_channel": "vscode_codex",
        "benchmark_root": os.getenv("ORIGINAL_IMAGE_ROOT", ""),
        "intake": {
            "job_postings": job_files,
            "hearings": hearing_files,
            "request_text": request_text_files,
            "job_only_mode": not hearing_files and not request_text_files,
        },
    }
    write_project_yaml(project_dir / "project.yaml", project_data)
    create_manifest(project_dir / "creative-manifest.csv", project_id, quantity)

    print(f"PROJECT_ID={project_id}")
    print(f"PROJECT_DIR={project_dir}")
    print(f"PROJECT_NAME={project_name}")
    print(f"JOB_POSTINGS={len(job_files)}")
    print(f"HEARING_INPUTS={len(hearing_files)}")
    print(f"REQUEST_TEXT_INPUTS={len(request_text_files)}")
    print(f"JOB_ONLY_MODE={str(not hearing_files and not request_text_files).lower()}")
    print(f"QUANTITY={quantity}")
    print(f"QUANTITY_SOURCE={quantity_source}")
    print("NEXT=prepare_creative_context.py -> VSCode Codex CCO")


if __name__ == "__main__":
    main()

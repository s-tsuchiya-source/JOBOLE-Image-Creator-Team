from pathlib import Path
import csv
import os
import re
from datetime import date, datetime

import yaml
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"
load_dotenv(ENV_PATH)

CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

MANIFEST_COLUMNS = [
    "project_id",
    "creative_group_id",
    "creative_id",
    "batch_id",
    "theme",
    "target",
    "message",
    "format",
    "width",
    "height",
    "copy_status",
    "art_status",
    "prompt_status",
    "generation_status",
    "review_status",
    "version",
    "claude_score",
    "codex_score",
    "final_score",
    "revision_count",
    "prompt_path",
    "image_path",
    "review_path",
    "cost_yen",
    "status",
    "updated_at",
]


def clean_input(value):
    return CONTROL_CHARS_RE.sub("", value).strip()


def ask(prompt):
    return clean_input(input(prompt))


def sanitize_name(text):
    text = clean_input(text).lower().replace(" ", "-")
    return re.sub(r"[^a-z0-9\-ぁ-んァ-ヶ一-龠]+", "-", text).strip("-")


def next_project_id(projects_root):
    ids = []
    if projects_root.exists():
        for path in projects_root.iterdir():
            if not path.is_dir():
                continue
            match = re.match(r"PJ-(\d{4})", path.name)
            if match:
                ids.append(int(match.group(1)))
    return f"PJ-{max(ids, default=0) + 1:04d}"


def create_manifest(path, project_id, quantity):
    now = datetime.now().isoformat(timespec="seconds")
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for i in range(1, quantity + 1):
            writer.writerow(
                {
                    "project_id": project_id,
                    "creative_id": f"CR{i:03d}",
                    "copy_status": "pending",
                    "art_status": "pending",
                    "prompt_status": "pending",
                    "generation_status": "pending",
                    "review_status": "pending",
                    "version": 0,
                    "revision_count": 0,
                    "cost_yen": 0,
                    "status": "pending",
                    "updated_at": now,
                }
            )


def read_quantity():
    raw = ask("制作枚数 (1〜100): ") or "1"
    try:
        quantity = int(raw)
    except ValueError:
        raise SystemExit("制作枚数は1〜100の整数で入力してください。")

    if not 1 <= quantity <= 100:
        raise SystemExit("制作枚数は1〜100の範囲で入力してください。")
    return quantity


def write_project_yaml(path, project_data):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(
            project_data,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )


def ensure_project_structure(project_dir):
    subdirs = [
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
    ]
    for subdir in subdirs:
        (project_dir / subdir).mkdir(parents=True, exist_ok=True)


def main():
    projects_root_value = os.getenv("PROJECTS_ROOT")
    if not projects_root_value:
        raise SystemExit(
            f"PROJECTS_ROOT が設定されていません。{ENV_PATH} の設定を確認してください。"
        )

    projects_root = Path(projects_root_value)
    projects_root.mkdir(parents=True, exist_ok=True)

    project_name = ask("案件名: ")
    client_name = ask("顧客名: ")
    objective = ask("目的: ")
    deadline = ask("納期 (YYYY-MM-DD): ")
    quantity = read_quantity()

    project_id = next_project_id(projects_root)
    slug = sanitize_name(client_name or project_name or "project") or "project"
    project_dir = projects_root / f"{project_id}_{slug}"
    ensure_project_structure(project_dir)

    project_data = {
        "project_id": project_id,
        "project_name": project_name,
        "client_name": client_name,
        "objective": objective,
        "deadline": deadline,
        "quantity": quantity,
        "created_at": date.today().isoformat(),
        "status": "awaiting_input",
        "input_status": "not_checked",
        "quality_mode": "quality_first",
        "human_final_approval_required": True,
    }

    write_project_yaml(project_dir / "project.yaml", project_data)
    create_manifest(project_dir / "creative-manifest.csv", project_id, quantity)

    print(f"案件を作成しました: {project_dir}")
    print("次に、求人原稿を 00_request/inbox/job_posting/ へ、")
    print("ヒアリング資料を 00_request/inbox/hearing/ へ配置してください。")
    print("参考画像・ロゴ等は 00_request/inbox/references/ へ配置できます。")


if __name__ == "__main__":
    main()

from pathlib import Path
import csv
import os
import re
from datetime import date

from dotenv import load_dotenv


# Always load .env from the repository root, regardless of the current directory.
REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"
load_dotenv(ENV_PATH)


def sanitize_name(text):
    text = text.strip().lower().replace(" ", "-")
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


def create_manifest(path, quantity):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["creative_id", "theme", "target", "format", "message", "status", "version", "score"])
        for i in range(1, quantity + 1):
            writer.writerow([f"CR{i:03d}", "", "", "", "", "pending", 0, ""])


def read_quantity():
    raw = input("制作枚数 (1〜100): ").strip() or "1"
    try:
        quantity = int(raw)
    except ValueError:
        raise SystemExit("制作枚数は1〜100の整数で入力してください。")

    if not 1 <= quantity <= 100:
        raise SystemExit("制作枚数は1〜100の範囲で入力してください。")
    return quantity


def main():
    projects_root_value = os.getenv("PROJECTS_ROOT")
    if not projects_root_value:
        raise SystemExit(
            f"PROJECTS_ROOT が設定されていません。{ENV_PATH} の設定を確認してください。"
        )

    projects_root = Path(projects_root_value)
    projects_root.mkdir(parents=True, exist_ok=True)

    project_name = input("案件名: ").strip()
    client_name = input("顧客名: ").strip()
    objective = input("目的: ").strip()
    deadline = input("納期 (YYYY-MM-DD): ").strip()
    quantity = read_quantity()

    project_id = next_project_id(projects_root)
    slug = sanitize_name(client_name or project_name or "project")
    project_dir = projects_root / f"{project_id}_{slug}"

    for subdir in [
        "00_request",
        "01_strategy",
        "02_direction",
        "03_batches",
        "04_project_review",
        "05_delivery",
    ]:
        (project_dir / subdir).mkdir(parents=True, exist_ok=True)

    project_yaml = f"""project_id: {project_id}
project_name: {project_name}
client_name: {client_name}
objective: {objective}
deadline: {deadline}
quantity: {quantity}
created_at: {date.today().isoformat()}
status: planning
"""

    (project_dir / "project.yaml").write_text(project_yaml, encoding="utf-8")
    create_manifest(project_dir / "creative-manifest.csv", quantity)

    print(f"案件を作成しました: {project_dir}")


if __name__ == "__main__":
    main()

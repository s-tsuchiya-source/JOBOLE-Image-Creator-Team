from __future__ import annotations

from collections import Counter
from datetime import date, datetime
import csv
import json
import os
from pathlib import Path
import sys

import yaml
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"
TMP_ROOT = REPO_ROOT / "tmp" / "current-project"


def load_environment() -> Path:
    load_dotenv(ENV_PATH)
    projects_root_value = os.getenv("PROJECTS_ROOT")
    if not projects_root_value:
        raise SystemExit(
            "PROJECTS_ROOT が設定されていません。"
            " リポジトリ直下の .env を確認してください。"
        )

    projects_root = Path(projects_root_value)
    if not projects_root.exists():
        raise SystemExit(f"PROJECTS_ROOT が存在しません: {projects_root}")
    return projects_root


def resolve_project_dir(projects_root: Path, project_key: str) -> Path:
    key = project_key.strip().lower()
    matches = [
        path
        for path in projects_root.iterdir()
        if path.is_dir() and path.name.lower().startswith(key)
    ]

    if not matches:
        raise SystemExit(f"案件が見つかりません: {project_key}")
    if len(matches) > 1:
        names = "\n".join(f"- {path.name}" for path in matches)
        raise SystemExit(
            f"案件指定が曖昧です。より具体的に指定してください: {project_key}\n{names}"
        )
    return matches[0]


def normalize_for_json(value):
    """Convert YAML-native values such as dates into JSON-safe values."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: normalize_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_for_json(item) for item in value]
    return value


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (yaml.YAMLError, UnicodeError) as exc:
        raise SystemExit(
            "project.yaml を読み込めません。YAML内に不正な文字または形式があります。\n"
            f"対象: {path}\n"
            "テスト案件の場合は案件フォルダを削除して new_project.py で再作成してください。\n"
            f"詳細: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise SystemExit(f"project.yaml のルートはオブジェクト形式である必要があります: {path}")

    return normalize_for_json(data)


def load_manifest(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_status_summary(rows: list[dict]) -> dict[str, int]:
    counts = Counter((row.get("status") or "unknown").strip() for row in rows)
    return dict(sorted(counts.items()))


def select_next_creatives(rows: list[dict], limit: int = 10) -> list[dict]:
    priority = {"revision": 0, "pending": 1, "review": 2, "planning": 3}
    candidates = [
        row
        for row in rows
        if (row.get("status") or "").strip() not in {"completed", "delivered"}
    ]
    candidates.sort(
        key=lambda row: (
            priority.get((row.get("status") or "").strip(), 99),
            row.get("creative_id") or "",
        )
    )
    return candidates[:limit]


def build_context(project_dir: Path, project: dict, rows: list[dict]) -> dict:
    return {
        "loaded_at": datetime.now().isoformat(timespec="seconds"),
        "project_dir": str(project_dir),
        "project": project,
        "manifest": {
            "total": len(rows),
            "status_summary": build_status_summary(rows),
            "next_creatives": select_next_creatives(rows),
        },
        "paths": {
            "project_yaml": str(project_dir / "project.yaml"),
            "creative_manifest": str(project_dir / "creative-manifest.csv"),
            "request": str(project_dir / "00_request"),
            "strategy": str(project_dir / "01_strategy"),
            "direction": str(project_dir / "02_direction"),
            "batches": str(project_dir / "03_batches"),
            "project_review": str(project_dir / "04_project_review"),
            "delivery": str(project_dir / "05_delivery"),
        },
    }


def write_context_files(context: dict) -> None:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)

    context_json = TMP_ROOT / "context.json"
    context_json.write_text(
        json.dumps(context, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    project = context.get("project", {})
    manifest = context.get("manifest", {})
    lines = [
        "# Current Project Context",
        "",
        f"- project_id: {project.get('project_id', '')}",
        f"- project_name: {project.get('project_name', '')}",
        f"- client_name: {project.get('client_name', '')}",
        f"- objective: {project.get('objective', '')}",
        f"- deadline: {project.get('deadline', '')}",
        f"- quantity: {project.get('quantity', '')}",
        f"- status: {project.get('status', '')}",
        "",
        "## Manifest Summary",
        f"- total: {manifest.get('total', 0)}",
    ]
    for status, count in manifest.get("status_summary", {}).items():
        lines.append(f"- {status}: {count}")

    lines.extend(["", "## Next Creatives"])
    for row in manifest.get("next_creatives", []):
        lines.append(
            f"- {row.get('creative_id', '')}: "
            f"status={row.get('status', '')}, "
            f"theme={row.get('theme', '')}, "
            f"format={row.get('format', '')}"
        )

    # UTF-8 with BOM keeps Japanese readable in Windows PowerShell 5.x Get-Content
    # while remaining safe for VS Code / Claude / Codex to read as Markdown.
    (TMP_ROOT / "context.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8-sig",
    )


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/load_project.py <project_id_or_folder_name>")

    projects_root = load_environment()
    project_dir = resolve_project_dir(projects_root, sys.argv[1])
    project = load_yaml(project_dir / "project.yaml")
    rows = load_manifest(project_dir / "creative-manifest.csv")
    context = build_context(project_dir, project, rows)
    write_context_files(context)

    print(f"案件を読み込みました: {project_dir.name}")
    print(f"制作数: {context['manifest']['total']}")
    print(f"状態: {context['manifest']['status_summary']}")
    print(f"Context: {TMP_ROOT / 'context.json'}")
    print(f"Summary: {TMP_ROOT / 'context.md'}")


if __name__ == "__main__":
    main()

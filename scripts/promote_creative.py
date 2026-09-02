from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env", override=True)

from scripts.load_project import load_environment, resolve_project_dir


REQUIRED_APPROVAL_FLAGS = [
    "creative_reviewer_pass",
    "codex_final_qa_pass",
    "fact_integrity_pass",
    "text_integrity_pass",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote a reviewed candidate to formal 05_delivery output.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--creative-id", default="CR001")
    parser.add_argument("--version", default="v001")
    parser.add_argument("--approval-file", required=True)
    parser.add_argument("--output-name", default="")
    args = parser.parse_args()

    projects_root = load_environment()
    project_dir = resolve_project_dir(projects_root, args.project_id)
    batch_dir = project_dir / "03_batches" / args.creative_id / args.version
    candidate = batch_dir / "candidate.png"
    expected_copy = batch_dir / "expected-copy.md"
    approval_path = Path(args.approval_file).expanduser().resolve()

    if not candidate.exists():
        raise SystemExit(f"candidate not found: {candidate}")
    if not approval_path.exists():
        raise SystemExit(f"approval file not found: {approval_path}")

    approval = json.loads(approval_path.read_text(encoding="utf-8-sig"))
    if str(approval.get("creative_id") or args.creative_id) != args.creative_id:
        raise SystemExit("approval creative_id does not match")
    if str(approval.get("version") or args.version) != args.version:
        raise SystemExit("approval version does not match")

    missing = [flag for flag in REQUIRED_APPROVAL_FLAGS if approval.get(flag) is not True]
    if missing:
        raise SystemExit("delivery blocked; missing approvals: " + ", ".join(missing))

    delivery_dir = project_dir / "05_delivery"
    delivery_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_name.strip() or f"{args.creative_id}.png"
    if Path(output_name).name != output_name:
        raise SystemExit("--output-name must be a file name, not a path")
    if not output_name.lower().endswith(".png"):
        output_name = Path(output_name).stem + ".png"

    final_image = delivery_dir / output_name
    final_copy = delivery_dir / f"{Path(output_name).stem}-copy.md"
    final_approval = delivery_dir / f"{Path(output_name).stem}-approval.json"

    shutil.copy2(candidate, final_image)
    if expected_copy.exists():
        shutil.copy2(expected_copy, final_copy)
    shutil.copy2(approval_path, final_approval)

    print("CREATIVE PROMOTION: PASS")
    print(f"IMAGE={final_image}")
    if final_copy.exists():
        print(f"COPY={final_copy}")
    print(f"APPROVAL={final_approval}")


if __name__ == "__main__":
    main()

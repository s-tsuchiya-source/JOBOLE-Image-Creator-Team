from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env", override=True)

from scripts.load_project import load_environment, resolve_project_dir
from services.creative_spec import load_creative_spec
from services.text_verifier import verify_image_text, write_verification


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify premium AI generated Japanese text against Creative Spec.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--creative-id", default="CR001")
    parser.add_argument("--version", default="v001")
    parser.add_argument("--observed-text-file", default="")
    args = parser.parse_args()

    projects_root = load_environment()
    project_dir = resolve_project_dir(projects_root, args.project_id)
    batch_dir = project_dir / "03_batches" / args.creative_id / args.version
    image_path = batch_dir / "candidate.png"
    spec_path = batch_dir / "creative-spec.json"
    report_path = project_dir / "04_project_review" / f"{args.creative_id}-{args.version}-text-verification.json"

    if not image_path.exists():
        raise SystemExit(f"candidate image not found: {image_path}")
    if not spec_path.exists():
        raise SystemExit(f"creative spec not found: {spec_path}")

    spec = load_creative_spec(spec_path)
    observed_text = None
    if args.observed_text_file.strip():
        observed_path = Path(args.observed_text_file).expanduser().resolve()
        observed_text = observed_path.read_text(encoding="utf-8-sig")

    report = verify_image_text(spec, image_path, observed_text=observed_text)
    report.update(
        {
            "project_id": args.project_id,
            "creative_id": args.creative_id,
            "version": args.version,
            "image": str(image_path),
            "creative_spec": str(spec_path),
        }
    )
    write_verification(report_path, report)

    print("TEXT VERIFICATION")
    print(f"STATUS={report.get('status')}")
    print(f"SOURCE={report.get('verification_source')}")
    print(f"REPORT={report_path}")
    if report.get("status") == "fail":
        raise SystemExit(3)


if __name__ == "__main__":
    main()

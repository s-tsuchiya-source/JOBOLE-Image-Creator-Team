from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from load_project import load_environment, resolve_project_dir
from services.contact_sheet import build_contact_sheet


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/build_contact_sheet.py <project_id>")
    root = load_environment()
    project_dir = resolve_project_dir(root, sys.argv[1])
    output = build_contact_sheet(project_dir)
    if output is None:
        raise SystemExit("No generated images were found in creative-manifest.csv")
    print(f"Contact sheet: {output}")


if __name__ == "__main__":
    main()

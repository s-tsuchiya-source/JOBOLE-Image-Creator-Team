from pathlib import Path
import csv
import sys


class ProjectManager:
    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self.manifest_path = self.project_dir / "creative-manifest.csv"

    def load_manifest(self):
        if not self.manifest_path.exists():
            return []
        with self.manifest_path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def summary(self):
        result = {}
        for row in self.load_manifest():
            status = row.get("status") or "unknown"
            result[status] = result.get(status, 0) + 1
        return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/project_manager.py <project_dir>")
    manager = ProjectManager(sys.argv[1])
    print(manager.summary())

"""Deprecated Phase 0 AI orchestrator entry point.

Phase 1 deliberately does NOT run Codex/Claude from Python.
The active workflow is orchestrated directly by VSCode Codex CCO according to
AGENTS.md and .codex/chief-creative-officer.md.

Python remains responsible only for file and image utilities.
"""


def main() -> None:
    print("run_production.py is deprecated for Phase 1.")
    print("")
    print("Current architecture:")
    print("  VSCode Codex CCO")
    print("    -> Claude Recruitment Analyst")
    print("    -> Codex Fact Check")
    print("    -> Claude Creative Director")
    print("    -> Codex Direction Approval")
    print("    -> Python image/file utilities")
    print("    -> Claude Creative Reviewer")
    print("    -> Codex Final QA")
    print("")
    print("Start an image-production request from VSCode Codex instead of this script.")
    print("See AGENTS.md for the Phase 1 operating procedure.")
    raise SystemExit(2)


if __name__ == "__main__":
    main()

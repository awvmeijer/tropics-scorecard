"""Collect the project's written documents into one file for NotebookLM.

Run after every milestone, then replace the "Tropics Scorecard digest" source
in the notebook with the new file. Standard library only.
"""
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "exports" / "notebook_digest.md"

SOURCES = [
    "README.md",
    "docs/verification_protocol.md",
    "docs/findings.md",
    "docs/failure_modes.md",
]


def main() -> None:
    parts = [f"# Tropics Scorecard digest, {date.today().isoformat()}\n"]
    paths = [ROOT / s for s in SOURCES]
    paths += sorted((ROOT / "docs" / "observation_notes").glob("*.md"))
    paths += sorted((ROOT / "docs" / "cases").glob("*.md")) if (ROOT / "docs" / "cases").exists() else []
    for path in paths:
        if not path.exists() or path.name == "TEMPLATE.md":
            continue
        parts.append(f"\n\n---\n\n<!-- {path.relative_to(ROOT)} -->\n\n")
        parts.append(path.read_text(encoding="utf-8"))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

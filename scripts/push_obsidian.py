#!/usr/bin/env python3
# huntd/scripts/push_obsidian.py
"""Push scored jobs from data/scored.md to a single Obsidian markdown table.

Writes {vault_path}/{folder}.md sorted by score descending.

Usage: python scripts/push_obsidian.py [--dry-run]
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from push_notion import extract_country, parse_scored_md

from config import ROOT, load_profile

VALID_STATUSES = {
    "New",
    "Saved",
    "Applied",
    "Interviewing",
    "Offer",
    "Rejected",
    "Dismissed",
}
VALID_WORK_TYPES = {"Remote", "Hybrid", "On-site", "Unknown"}


def _coerce(value: str, valid: set, default: str) -> str:
    return value if value in valid else default


def build_table_file(jobs: list, date_str: str) -> str:
    sorted_jobs = sorted(jobs, key=lambda x: -x.get("score", 0))

    lines = [
        "# Job Pipeline",
        f"_Updated: {date_str} · {len(jobs)} jobs_",
        "",
        "| Company | Role | Score | Status | Work Type | Location |",
        "|---------|------|-------|--------|-----------|----------|",
    ]

    for j in sorted_jobs:
        company = j.get("company", "?")
        title = j.get("title", "?")
        url = j.get("url", "")
        role = f"[{title}]({url})" if url else title
        score = int(j.get("score", 0))
        status = _coerce(j.get("status", ""), VALID_STATUSES, "New")
        work_type = _coerce(j.get("work_type", ""), VALID_WORK_TYPES, "Unknown")
        location = extract_country(j.get("location", ""))
        lines.append(
            f"| {company} | {role} | {score} | {status} | {work_type} | {location} |"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    dry_run = "--dry-run" in sys.argv

    try:
        profile = load_profile()
    except FileNotFoundError as e:
        console.print(f"[bold red]ERROR:[/] {e}")
        sys.exit(1)

    obs = profile.get("obsidian", {}) or {}
    vault_path = (obs.get("vault_path") or "").strip()
    folder_name = (obs.get("folder") or "Jobs").strip() or "Jobs"

    if not vault_path:
        console.print(
            "[bold red]ERROR:[/] obsidian.vault_path is not set in config/profile.yml.\n"
            "Tell your AI: [bold]'set my Obsidian vault path to /path/to/vault'[/]"
        )
        sys.exit(1)

    vault = Path(vault_path).expanduser()
    if not dry_run and not vault.exists():
        console.print(f"[bold red]ERROR:[/] Vault path does not exist: {vault}")
        sys.exit(1)

    output_file = vault / f"{folder_name}.md"

    scored_path = ROOT / "data" / "scored.md"
    if not scored_path.exists():
        console.print(
            "[dim]data/scored.md not found. Run [bold]/huntd score[/] first.[/]"
        )
        sys.exit(0)

    jobs = parse_scored_md(scored_path.read_text())
    if not jobs:
        console.print("[dim]No scored jobs found in data/scored.md[/]")
        sys.exit(0)

    today = date.today().isoformat()

    mode_label = "[bold yellow]DRY RUN[/] · " if dry_run else ""
    console.print(
        Panel(
            f"{mode_label}[bold cyan]{len(jobs)}[/] jobs → [dim]{output_file}[/]",
            title="[bold]huntd push --obsidian[/]",
            border_style="cyan",
        )
    )

    if dry_run:
        console.print(f"[dim]Would write {output_file}[/]")
        sys.exit(0)

    content = build_table_file(jobs, today)
    output_file.write_text(content, encoding="utf-8")
    console.print(f"[green]Written:[/] {output_file}")


if __name__ == "__main__":
    main()

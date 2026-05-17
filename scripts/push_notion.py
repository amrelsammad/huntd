#!/usr/bin/env python3
# huntd/scripts/push_notion.py
"""Push scored jobs from data/scored.md to Notion.

Usage: python scripts/push_notion.py [--dry-run]
"""

import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import load_profile, ROOT

NOTION_API = "https://api.notion.com/v1"

VALID_STATUSES = {"New", "Saved", "Applied", "Interviewing", "Offer", "Rejected", "Dismissed"}
VALID_WORK_TYPES = {"Remote", "Hybrid", "On-site", "Unknown"}

# City → country fallback for when the country isn't explicit in the location string
_CITIES = {
    "san francisco": "United States", "new york": "United States", "seattle": "United States",
    "boston": "United States", "austin": "United States", "chicago": "United States",
    "los angeles": "United States", "denver": "United States", "miami": "United States",
    "washington": "United States", "palo alto": "United States", "mountain view": "United States",
    "london": "United Kingdom", "manchester": "United Kingdom", "edinburgh": "United Kingdom",
    "berlin": "Germany", "munich": "Germany", "hamburg": "Germany",
    "amsterdam": "Netherlands", "rotterdam": "Netherlands",
    "dubai": "UAE", "abu dhabi": "UAE", "sharjah": "UAE",
    "riyadh": "Saudi Arabia", "jeddah": "Saudi Arabia",
    "cairo": "Egypt", "alexandria": "Egypt",
    "singapore": "Singapore",
    "toronto": "Canada", "vancouver": "Canada", "montreal": "Canada",
    "sydney": "Australia", "melbourne": "Australia",
    "bangalore": "India", "bengaluru": "India", "mumbai": "India",
    "delhi": "India", "hyderabad": "India", "pune": "India",
    "paris": "France", "barcelona": "Spain", "madrid": "Spain",
    "warsaw": "Poland", "krakow": "Poland", "tallinn": "Estonia",
    "taipei": "Taiwan", "hong kong": "Hong Kong", "tokyo": "Japan", "seoul": "South Korea",
    "tel aviv": "Israel", "stockholm": "Sweden", "copenhagen": "Denmark",
    "oslo": "Norway", "helsinki": "Finland", "dublin": "Ireland",
    "zurich": "Switzerland", "lisbon": "Portugal", "milan": "Italy",
    "prague": "Czech Republic", "bangkok": "Thailand", "jakarta": "Indonesia",
    "kuala lumpur": "Malaysia", "manila": "Philippines",
    "sao paulo": "Brazil", "buenos aires": "Argentina", "mexico city": "Mexico",
    "lagos": "Nigeria", "cape town": "South Africa", "johannesburg": "South Africa",
    "casablanca": "Morocco", "amman": "Jordan", "doha": "Qatar",
    "manama": "Bahrain", "istanbul": "Turkey", "kuwait city": "Kuwait",
}

# Common abbreviations and shorthand → canonical country name
_ABBREV = {
    "usa": "United States", "us": "United States", "united states": "United States",
    "uk": "United Kingdom", "united kingdom": "United Kingdom", "gb": "United Kingdom",
    "uae": "UAE", "united arab emirates": "UAE",
    "ksa": "Saudi Arabia", "kingdom of saudi arabia": "Saudi Arabia", "saudi": "Saudi Arabia",
    "eu": "Europe",
}


def _rt(text: str) -> list:
    """Notion rich_text block, capped at 2000 chars."""
    return [{"text": {"content": str(text)[:2000]}}]


def _coerce_select(value: str, valid: set, default: str) -> str:
    return value if value in valid else default


def _source(value: str) -> str:
    """Return source as-is (Notion auto-creates select options); fall back to Unknown."""
    return value.strip() if value and value.strip() else "Unknown"


def extract_country(raw: str) -> str:
    """Normalize a raw ATS location string to a country name for the Notion select field."""
    import pycountry
    loc = (raw or "").lower().strip()
    if not loc:
        return "Unknown"

    # 1. Abbreviations / shorthand (word-boundary matched)
    for abbrev, country in _ABBREV.items():
        if re.search(r"\b" + re.escape(abbrev) + r"\b", loc):
            return country

    # 2. Full pycountry country names (longest first to avoid partial hits)
    for c in sorted(pycountry.countries, key=lambda c: len(c.name), reverse=True):
        if c.name.lower() in loc:
            return c.name

    # 3. City dict fallback
    for city, country in _CITIES.items():
        if city in loc:
            return country

    return "Unknown"


def push_job(job: dict, token: str, db_id: str) -> bool:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    payload = {
        "parent": {"database_id": db_id},
        "properties": {
            "Job Title": {"title": _rt(job.get("title", "Untitled"))},
            "Company": {"rich_text": _rt(job.get("company", ""))},
            "Location": {"select": {"name": extract_country(job.get("location", ""))}},
            "Work Type": {"select": {"name": _coerce_select(job.get("work_type", ""), VALID_WORK_TYPES, "Unknown")}},
            "Source": {"select": {"name": _source(job.get("source", ""))}},
            "Fit Score": {"number": float(job.get("score", 5.0))},
            "Status": {"select": {"name": _coerce_select(job.get("status", ""), VALID_STATUSES, "New")}},
            "Fit Reasons": {"rich_text": _rt(job.get("fit_reasons", ""))},
            "Red Flags": {"rich_text": _rt(job.get("red_flags", ""))},
            "Link": {"url": job["url"]},
        },
    }
    try:
        resp = requests.post(f"{NOTION_API}/pages", json=payload, headers=headers, timeout=15)
    except requests.RequestException as e:
        print(f"  [ERROR] Network error: {e}")
        return False
    if resp.status_code != 200:
        print(f"  [ERROR] Notion API {resp.status_code}: {resp.text[:200]}")
        return False
    return True


def validate_notion(token: str, db_id: str) -> tuple[bool, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
    }
    try:
        resp = requests.get(f"{NOTION_API}/databases/{db_id}", headers=headers, timeout=10)
    except requests.RequestException as e:
        return False, str(e)
    if resp.ok:
        return True, ""
    return False, f"HTTP {resp.status_code}: {resp.text[:200]}"


def parse_scored_md(text: str) -> list[dict]:
    """Parse scored.md into list of job dicts.

    Expected format per entry:
        ### Company — Title
        - **URL:** https://...
        - **Score:** 8/10
        - **Status:** New
        - **Location:** Remote
        - **Source:** Greenhouse
        - **Fit Reasons:** • Reason 1 • Reason 2
        - **Red Flags:** None
    """
    jobs = []
    entries = re.split(r"\n(?=### )", text)
    for entry in entries:
        if not entry.startswith("### "):
            continue
        job: dict = {}
        lines = entry.strip().splitlines()
        header = lines[0][4:].strip()
        if " — " in header:
            job["company"], job["title"] = header.split(" — ", 1)
        elif " - " in header:
            job["company"], job["title"] = header.split(" - ", 1)
        else:
            job["title"] = header
            job["company"] = "Unknown"

        for line in lines[1:]:
            line = line.strip()
            if not line.startswith("- **"):
                continue
            if "**URL:**" in line:
                job["url"] = line.split("**URL:**", 1)[1].strip()
            elif "**Score:**" in line:
                m = re.search(r"([\d.]+)", line.split("**Score:**", 1)[1])
                job["score"] = float(m.group()) if m else 5.0
            elif "**Status:**" in line:
                job["status"] = line.split("**Status:**", 1)[1].strip()
            elif "**Location:**" in line:
                job["location"] = line.split("**Location:**", 1)[1].strip()
            elif "**Work Type:**" in line:
                job["work_type"] = line.split("**Work Type:**", 1)[1].strip()
            elif "**Source:**" in line:
                job["source"] = line.split("**Source:**", 1)[1].strip()
            elif "**Fit Reasons:**" in line:
                job["fit_reasons"] = line.split("**Fit Reasons:**", 1)[1].strip()
            elif "**Red Flags:**" in line:
                job["red_flags"] = line.split("**Red Flags:**", 1)[1].strip()

        if "url" in job and "title" in job:
            jobs.append(job)

    return jobs


def main() -> None:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    console = Console()
    dry_run = "--dry-run" in sys.argv

    try:
        profile = load_profile()
    except FileNotFoundError as e:
        console.print(f"[bold red]ERROR:[/] {e}")
        sys.exit(1)
    notion = profile.get("notion", {})
    token = notion.get("token", "")
    db_id = notion.get("database_id", "")

    if not token or not db_id:
        console.print(
            "[bold red]ERROR:[/] Notion token and database_id must be set. "
            "Tell your AI: 'set up my Notion credentials'"
        )
        sys.exit(1)

    if not dry_run:
        ok, err = validate_notion(token, db_id)
        if not ok:
            console.print(f"[bold red]ERROR:[/] Notion credentials invalid: {err}")
            sys.exit(1)

    path = ROOT / "data" / "scored.md"
    if not path.exists():
        console.print("[dim]data/scored.md not found. Run [bold]/huntd score[/] first.[/]")
        sys.exit(0)

    jobs = parse_scored_md(path.read_text())
    if not jobs:
        console.print("[dim]No scored jobs in data/scored.md[/]")
        sys.exit(0)

    mode = "[bold yellow]DRY RUN[/] · " if dry_run else ""
    console.print(Panel(
        f"{mode}Pushing [bold cyan]{len(jobs)}[/] jobs to Notion",
        title="[bold]huntd push[/]",
        border_style="cyan",
    ))

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim")
    table.add_column("Company — Title", style="white")
    table.add_column("Score", justify="right")
    table.add_column("Status", justify="center")

    pushed = 0
    for job in jobs:
        label = f"{job.get('company', '?')} — {job.get('title', '?')}"
        score_str = f"{job.get('score', '?')}/10"
        if dry_run:
            table.add_row(label, score_str, "[yellow]preview[/]")
            pushed += 1
        elif push_job(job, token, db_id):
            table.add_row(label, score_str, "[green]pushed[/]")
            pushed += 1
        else:
            table.add_row(label, score_str, "[red]failed[/]")

    console.print(table)
    verb = "previewed" if dry_run else "pushed to Notion"
    console.print(f"[dim]{pushed}/{len(jobs)} jobs {verb}[/]")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# huntd/scripts/scan.py
"""Scan ATS job boards and add new jobs to data/pipeline.md.

Usage: python scripts/scan.py
"""

import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    load_portals,
    load_seen,
    load_pipeline_urls,
    save_seen,
    append_to_pipeline,
    job_id,
)


def fetch_greenhouse(slug: str, company_name: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        print(f"  [ERROR] Greenhouse {slug}: {e}")
        return []
    if not resp.ok:
        print(f"  [WARN] Greenhouse {slug}: HTTP {resp.status_code}")
        return []
    jobs = []
    for j in resp.json().get("jobs", []):
        title = j.get("title", "")
        url = j.get("absolute_url", "")
        if not title or not url:
            continue
        jobs.append({
            "title": title,
            "url": url,
            "company": company_name,
            "location": (j.get("location") or {}).get("name", "") or "",
            "source": "Greenhouse",
        })
    return jobs


def fetch_lever(slug: str, company_name: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{slug}"
    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        print(f"  [ERROR] Lever {slug}: {e}")
        return []
    if not resp.ok:
        print(f"  [WARN] Lever {slug}: HTTP {resp.status_code}")
        return []
    jobs = []
    for j in resp.json():
        title = j.get("text", "")
        url = j.get("hostedUrl", "")
        if not title or not url:
            continue
        jobs.append({
            "title": title,
            "url": url,
            "company": company_name,
            "location": (j.get("categories") or {}).get("location", "") or "",
            "source": "Lever",
        })
    return jobs


def fetch_ashby(slug: str, company_name: str) -> list[dict]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        print(f"  [ERROR] Ashby {slug}: {e}")
        return []
    if resp.status_code == 404:
        print(f"  [WARN] Ashby {slug}: board not found or public API not enabled for this company")
        return []
    if not resp.ok:
        print(f"  [WARN] Ashby {slug}: HTTP {resp.status_code}")
        return []
    jobs = []
    for j in resp.json().get("jobs", []):
        title = j.get("title", "")
        job_url = j.get("jobUrl", "")
        if not title or not job_url:
            continue
        jobs.append({
            "title": title,
            "url": job_url,
            "company": company_name,
            "location": j.get("location", "") or "",
            "source": "Ashby",
        })
    return jobs


def fetch_smartrecruiters(slug: str, company_name: str) -> list[dict]:
    url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        print(f"  [ERROR] SmartRecruiters {slug}: {e}")
        return []
    if not resp.ok:
        print(f"  [WARN] SmartRecruiters {slug}: HTTP {resp.status_code}")
        return []
    jobs = []
    for j in resp.json().get("content", []):
        title = j.get("name", "")
        job_url = j.get("ref", "")
        if not title or not job_url:
            continue
        loc = j.get("location", {})
        location = ", ".join(filter(None, [loc.get("city"), loc.get("country")]))
        jobs.append({
            "title": title,
            "url": job_url,
            "company": company_name,
            "location": location,
            "source": "SmartRecruiters",
        })
    return jobs


FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "smartrecruiters": fetch_smartrecruiters,
}


def passes_filters(job: dict, filters: dict) -> bool:
    title = job["title"].lower()
    title_cfg = filters.get("title", {})

    required_any = [k.lower() for k in title_cfg.get("required_any", [])]
    if required_any and not any(k in title for k in required_any):
        return False

    excluded = [k.lower() for k in title_cfg.get("excluded", [])]
    if any(k in title for k in excluded):
        return False

    location = job.get("location", "").lower()
    loc_cfg = filters.get("location", {})

    blocked = [b.lower() for b in loc_cfg.get("block", [])]
    if blocked and any(b in location for b in blocked):
        return False

    allowed = [a.lower() for a in loc_cfg.get("allow", [])]
    # If location is empty, we can't filter it — let it through
    if allowed and location and not any(a in location for a in allowed):
        return False

    return True


def main() -> None:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    console = Console()

    portals = load_portals()
    seen = load_seen()
    in_pipeline = load_pipeline_urls()
    already_seen = seen | {job_id(u) for u in in_pipeline}

    companies = [c for c in portals.get("tracked_companies", []) if c.get("enabled", True)]
    filters = portals.get("filters", {})

    console.print(Panel(
        f"Scanning [bold cyan]{len(companies)}[/] companies across Greenhouse · Ashby · Lever · SmartRecruiters",
        title="[bold]huntd scan[/]",
        border_style="cyan",
    ))

    total_fetched = 0
    new_jobs: list[dict] = []
    results = []

    for company in companies:
        ats = company.get("ats", "")
        slug = company.get("board_slug", "")
        name = company.get("name", slug)

        fetcher = FETCHERS.get(ats)
        if not fetcher:
            console.print(
                f"  [yellow]WARN[/] {name}: ATS type '[bold]{ats}[/]' has no scraper — skipping. "
                f"(Supported: {', '.join(sorted(FETCHERS.keys()))})"
            )
            results.append((name, ats, 0, 0, f"no scraper for '{ats}'"))
            continue

        jobs = fetcher(slug, name)
        total_fetched += len(jobs)
        company_new = 0

        for job in jobs:
            uid = job_id(job["url"])
            if uid in already_seen:
                continue
            if not passes_filters(job, filters):
                continue
            new_jobs.append(job)
            already_seen.add(uid)
            seen.add(uid)
            company_new += 1

        results.append((name, ats, len(jobs), company_new, ""))
        time.sleep(0.5)

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim")
    table.add_column("Company", style="white")
    table.add_column("ATS", style="dim")
    table.add_column("Found", justify="right", style="dim")
    table.add_column("New", justify="right")

    for name, ats, found, new_count, note in results:
        if note:
            new_str = f"[red]{note}[/]"
        elif new_count > 0:
            new_str = f"[bold cyan]{new_count}[/]"
        else:
            new_str = "[dim]0[/]"
        table.add_row(name, ats, str(found), new_str)

    console.print(table)

    if new_jobs:
        append_to_pipeline(new_jobs)
        save_seen(seen)
        console.print(Panel(
            f"[bold cyan]{len(new_jobs)}[/] new jobs added to [dim]data/pipeline.md[/]\n"
            f"Run [bold]/huntd score[/] to evaluate them.",
            border_style="cyan",
        ))
    else:
        console.print("[dim]No new jobs found after filtering.[/]")


if __name__ == "__main__":
    main()

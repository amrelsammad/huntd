#!/usr/bin/env python3
# huntd/scripts/score_batch.py
"""Automated batch scoring using Gemini API. Used by the scheduler cron job.

Usage: python scripts/score_batch.py
Requires: automation.gemini_api_key in config/profile.yml
"""

import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import load_profile, ROOT


def fetch_jd(url: str) -> str:
    """Fetch job description text from a job URL. Returns empty string on failure."""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if not resp.ok:
            return ""
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:8000]
    except requests.RequestException:
        return ""


def score_job_with_gemini(
    model,
    resume: str,
    profile_md: str,
    job_line: str,
) -> dict | None:
    """Score a single pipeline.md job line using the Gemini model."""
    stripped = job_line.lstrip("- [ ] ").strip()
    parts = stripped.split(" | ")
    if len(parts) < 4:
        return None
    url, company, title, location = (
        parts[0].strip(),
        parts[1].strip(),
        parts[2].strip(),
        parts[3].strip(),
    )

    jd_text = fetch_jd(url)
    jd_section = (
        f"\n\nJob Description:\n{jd_text}"
        if jd_text
        else "\n\n(Job description unavailable — scoring from title and company only)"
    )

    prompt = f"""You are scoring a job opportunity against a candidate's resume and profile.

Resume:
{resume}

Candidate Profile (scoring weights and deal-breakers):
{profile_md}

Job to score:
- Company: {company}
- Title: {title}
- Location: {location}
- URL: {url}{jd_section}

Score this job 1-10 based on fit. Check deal-breakers first — if any apply, score maximum 3 and set status to Dismissed.
Also determine the work arrangement from the job description: Remote (fully remote), Hybrid (remote + office), On-site (office only), or Unknown.

Respond ONLY in this exact format (no other text):
SCORE: <number>
STATUS: <New|Dismissed>
WORK_TYPE: <Remote|Hybrid|On-site|Unknown>
FIT_REASONS: <bullet points separated by •>
RED_FLAGS: <issues or "None">"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
    except Exception as e:
        print(f"  [API ERROR] {company} — {title}: {e}")
        return None

    result = {
        "url": url,
        "company": company,
        "title": title,
        "location": location,
        "source": "Unknown",
    }
    for line in text.splitlines():
        if line.startswith("SCORE:"):
            m = re.search(r"([\d.]+)", line)
            result["score"] = float(m.group()) if m else 5.0
        elif line.startswith("STATUS:"):
            result["status"] = line.split(":", 1)[1].strip()
        elif line.startswith("WORK_TYPE:"):
            result["work_type"] = line.split(":", 1)[1].strip()
        elif line.startswith("FIT_REASONS:"):
            result["fit_reasons"] = line.split(":", 1)[1].strip()
        elif line.startswith("RED_FLAGS:"):
            result["red_flags"] = line.split(":", 1)[1].strip()

    if "score" not in result:
        return None
    return result


def append_to_scored(job: dict) -> None:
    path = ROOT / "data" / "scored.md"
    if not path.exists():
        path.write_text("# Scored Jobs — Pending Notion Push\n\n")
    with open(path, "a") as f:
        f.write(
            f"\n### {job['company']} — {job['title']}\n"
            f"- **URL:** {job['url']}\n"
            f"- **Score:** {job['score']}/10\n"
            f"- **Status:** {job.get('status', 'New')}\n"
            f"- **Location:** {job['location']}\n"
            f"- **Work Type:** {job.get('work_type', 'Unknown')}\n"
            f"- **Source:** {job.get('source', 'Unknown')}\n"
            f"- **Fit Reasons:** {job.get('fit_reasons', '')}\n"
            f"- **Red Flags:** {job.get('red_flags', 'None')}\n"
        )


def mark_scored_in_pipeline(url: str) -> None:
    path = ROOT / "data" / "pipeline.md"
    if not path.exists():
        return
    text = path.read_text()
    text = text.replace(f"- [ ] {url}", f"- [x] {url}", 1)
    path.write_text(text)


def main() -> None:
    try:
        profile = load_profile()
    except FileNotFoundError as e:
        print(f"SKIP: {e}")
        sys.exit(0)
    api_key = profile.get("automation", {}).get("gemini_api_key", "").strip()

    if not api_key:
        print("SKIP: No gemini_api_key in config/profile.yml — skipping automated scoring.")
        print("      Run /huntd score manually in your AI CLI to score pending jobs.")
        sys.exit(0)

    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    resume_path = ROOT / "resume.md"
    profile_md_path = ROOT / "modes" / "_profile.md"

    if not resume_path.exists():
        print("ERROR: resume.md not found. Run /huntd setup first.")
        sys.exit(1)
    if not profile_md_path.exists():
        print("ERROR: modes/_profile.md not found. Run /huntd setup first.")
        sys.exit(1)

    resume = resume_path.read_text()
    profile_md = profile_md_path.read_text()

    pipeline_path = ROOT / "data" / "pipeline.md"
    if not pipeline_path.exists():
        print("No pipeline.md found. Run scan first.")
        sys.exit(0)

    pending = [
        line
        for line in pipeline_path.read_text().splitlines()
        if line.startswith("- [ ]")
    ]

    if not pending:
        print("No pending jobs to score.")
        sys.exit(0)

    print(f"Scoring {len(pending)} pending jobs via Gemini API...")
    scored = 0
    for job_line in pending:
        job = score_job_with_gemini(model, resume, profile_md, job_line)
        if job:
            append_to_scored(job)
            mark_scored_in_pipeline(job["url"])
            print(f"  ✓ {job['company']} — {job['title']} → {job['score']}/10")
            scored += 1
        time.sleep(1.5)  # stay under free-tier rate limit

    print(f"Scored {scored}/{len(pending)} jobs.")


if __name__ == "__main__":
    main()

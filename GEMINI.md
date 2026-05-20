<!-- huntd/GEMINI.md -->
# huntd — Job Hunting Assistant (Gemini CLI)

huntd is free to use with Gemini CLI (no subscription required).
It scans ATS job boards (Greenhouse, Ashby, Lever, SmartRecruiters, Workable), scores jobs using your AI session, and pushes results to Notion.

## Quickstart (Gemini CLI)

```bash
cd huntd
curl -LsSf https://astral.sh/uv/install.sh | sh  # install uv (once)
uv sync                                            # install dependencies
gemini "run /huntd setup"
```

Setup will ask you to drag your resume (PDF or DOCX) into the terminal — this pastes the file path without moving the file. huntd then parses it and automatically generates your profile and a starter company list. No YAML editing required.

## Commands

Say these naturally or use the slash format:

| Command | Natural language equivalent |
|---------|-----------------------------|
| `/huntd setup` | "set me up" / "first time setup" |
| `/huntd scan` | "scan for new jobs" |
| `/huntd score` | "score the pending jobs" |
| `/huntd push` | "push scored jobs to Notion" |
| `/huntd push --dry-run` | "show me what would be pushed" |
| `/huntd status` | "how many jobs are in the pipeline?" |
| `/huntd schedule enable` | "run huntd automatically every day" |
| `/huntd schedule disable` | "turn off the daily schedule" |
| `/huntd schedule status` | "when does huntd run?" |
| `/huntd update` | "update huntd" / "get the latest version" |

## Updating your profile or companies

Just tell me what to change:
- "Add Stripe to my tracked companies"
- "I'm also open to Director-level roles now"
- "Remove on-site roles as a deal-breaker"

I'll update the config files and confirm what changed.

## Instructions (read these first)

All instructions live in `modes/`:
- **`modes/_shared.md`** — data formats, Notion schema, global rules. **Read this first.**
- **`modes/score.md`** — scoring protocol (step-by-step)
- **`modes/_profile.md`** — your personal scoring weights (auto-generated from resume during setup)

## Search queries (Bayt, GulfTalent, LinkedIn)

`/huntd scan` also processes any `search_queries` configured in `config/portals.yml`. These are site-filtered WebSearch queries (e.g., `site:bayt.com "product manager" Dubai`) that discover jobs from portals without public APIs.

The automated daily cron only runs ATS scrapers. Search queries need an active Gemini session.

## What huntd does NOT do
- Auto-apply to jobs
- Customize CVs per job
- Call any external AI API (all scoring happens in your Gemini session)

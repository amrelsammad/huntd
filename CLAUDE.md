<!-- huntd/CLAUDE.md -->
# huntd — Job Hunting Assistant (Claude Code)

> huntd works free with Gemini CLI. This file loads it for Claude Code users.

huntd is a terminal job hunting tool. It scans ATS job boards (Greenhouse, Ashby, Lever, SmartRecruiters, Workable), scores jobs using in-session AI reasoning (no external API), and pushes curated results to Notion.

## How to use

Run `/huntd` followed by a command:

| Command | What it does |
|---------|-------------|
| `/huntd setup` | First-run: drag resume into terminal → parses it → generates profile + company list |
| `/huntd scan` | Fetch new jobs from ATS boards → `data/pipeline.md` |
| `/huntd score` | Score pending jobs → `data/scored.md` |
| `/huntd push` | Push scored jobs to Notion |
| `/huntd push --dry-run` | Preview Notion push without sending |
| `/huntd status` | Show pipeline stats |
| `/huntd update` | Pull latest huntd updates + reinstall deps |
| `/huntd schedule enable` | Install daily cron job (scan → score → push) |
| `/huntd schedule disable` | Remove the cron job |
| `/huntd schedule status` | Show if the schedule is active |

## Updating your profile or company list

Users never need to edit YAML files directly. Instead, they ask you:
- "Add Figma to my tracked companies"
- "I'm also open to Head of Product roles"
- "Remove fintech from my target industries"

When asked, read the relevant config file, make the change, confirm what you changed.

## Instructions

All instructions live in `modes/`:
- `modes/_shared.md` — data formats, Notion schema, global rules
- `modes/score.md` — step-by-step scoring protocol
- `modes/_profile.md` — scoring weights and deal-breakers (generated from resume during setup)

**Read `modes/_shared.md` at the start of every session.**

## What huntd does NOT do
- Auto-apply to jobs
- Customize CVs per job
- Call any external AI API (all reasoning is done in this session)

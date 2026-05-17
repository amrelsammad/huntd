<!-- huntd/AGENTS.md -->
# huntd — Job Hunting Assistant (Codex / OpenAI CLI)

huntd works with any AI coding CLI that reads an AGENTS.md file.
It scans ATS job boards, scores jobs in-session, and pushes results to Notion.

## Commands

| Command | What it does |
|---------|-------------|
| `/huntd setup` | First-run: drag resume into terminal → parse → generate profile + company list |
| `/huntd scan` | Run `uv run python scripts/scan.py` — fetch new jobs |
| `/huntd score` | Score pending jobs from `data/pipeline.md` → `data/scored.md` |
| `/huntd push` | Run `uv run python scripts/push_notion.py` — push to Notion |
| `/huntd push --dry-run` | Preview push without sending |
| `/huntd status` | Show pipeline stats |
| `/huntd update` | `git pull && uv sync` — apply latest changes |

## Instructions

Read these mode files at session start:
- `modes/_shared.md` — system context, data formats, global rules
- `modes/score.md` — scoring protocol
- `modes/_profile.md` — user's personal weights and deal-breakers

## Session start
Run `uv run python scripts/check_update.py` at the start of every session. Show any output to the user.

## Rules
- Never score without reading `resume.md` first
- Never call external AI APIs
- Never auto-apply to jobs

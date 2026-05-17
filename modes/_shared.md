# huntd — System Context

## Project Purpose
huntd discovers job opportunities from ATS job boards, evaluates them against the candidate's profile, and pushes curated results to a Notion database.

## Key Files (AI reads these)
- `resume.md` — Candidate's full resume (parsed from PDF/DOCX during setup). **Always read before scoring.**
- `modes/_profile.md` — Scoring weights, deal-breakers, target archetypes. **Always read before scoring.**
- `config/profile.yml` — Target roles, locations, seniority. Reference when _profile.md doesn't cover a case.
- `data/pipeline.md` — Jobs to score (lines with `- [ ]`).
- `data/scored.md` — Jobs already scored, pending Notion push.

## search_queries

`search_queries` in `config/portals.yml` is an optional list of Google-compatible site-filtered queries (e.g., `site:bayt.com "product manager" Dubai`). Run during in-session scanning (Claude/Gemini WebSearch) — not by the automated cron (`scripts/scan.py`). Source is inferred from the `site:` domain in the query. Results are deduplicated against `data/seen.json`.

---

## Data Formats

### data/pipeline.md entry format
```
- [ ] {url} | {company} | {title} | {location}
```
After scoring, mark as:
```
- [x] {url} | {company} | {title} | {location}
```

### data/scored.md entry format
Each entry MUST follow this exact structure (push_notion.py parses it):
```markdown
### {Company} — {Title}
- **URL:** {url}
- **Score:** {1-10}/10
- **Status:** {New|Saved|Applied|Dismissed}
- **Location:** {raw location string from ATS}
- **Work Type:** {Remote|Hybrid|On-site|Unknown}
- **Source:** {Greenhouse|Ashby|Lever|LinkedIn|Bayt|Unknown|...}
- **Fit Reasons:** {bullet list, use • as separator or newlines}
- **Red Flags:** {concerns, or "None"}
```

## Notion Database Schema
Properties that push_notion.py expects (exact names):

| Property | Type | Valid values |
|----------|------|-------------|
| Job Title | title | any |
| Company | rich_text | any |
| Location | select | Country name — auto-created (e.g. United States, UAE, Germany) |
| Work Type | select | Remote, Hybrid, On-site, Unknown |
| Source | select | Any — auto-created from ATS type (Greenhouse, Ashby, Lever, Bayt…) |
| Fit Score | number | 1.0 – 10.0 |
| Status | select | New, Saved, Applied, Interviewing, Offer, Rejected, Dismissed |
| Fit Reasons | rich_text | any (max 2000 chars) |
| Red Flags | rich_text | any (max 2000 chars) |
| Link | url | valid URL |

## Global Rules
- **Never score without reading resume.md** — the resume is the ground truth for fit evaluation.
- **Never invent skills** the candidate doesn't have. Score what's actually there.
- **Dismiss with honesty** — if a job clearly fails deal-breakers, mark Status=Dismissed and explain why in Red Flags.
- **Fetch the JD before scoring** — use WebFetch on the job URL for the full job description. If fetch fails, score based on title + company context.
- **Never ask the user to edit config files directly** — when they ask to update something, read the file, make the change, write it back, confirm.

## Conversational Profile Updates

When the user asks to update their profile, targets, or company list:

| User says | File to update | What to change |
|-----------|---------------|----------------|
| "Add [company] to my tracked companies" | `config/portals.yml` | Add entry to `tracked_companies` |
| "Remove [company]" | `config/portals.yml` | Set `enabled: false` or delete entry |
| "I'm also interested in [role]" | `config/profile.yml` | Add to `targets.roles` |
| "Remove [industry] from my targets" | `config/profile.yml` | Remove from `targets.industries` |
| "Add [location] as a target" | `config/profile.yml` | Add to `targets.locations` |
| "Add a Bayt/GulfTalent/LinkedIn search for [role] in [location]" | `config/portals.yml` | Add to `search_queries` |
| "Remove all [portal] searches" | `config/portals.yml` | Remove matching entries from `search_queries` |
| "Make [thing] a deal-breaker" | `modes/_profile.md` | Add to deal-breakers list |
| "Enable the daily schedule" | ask preferred time → update `profile.yml` → run `scheduler.py enable` | Install cron |
| "Change my schedule to [time]" | update `profile.yml` `schedule.time` → run `scheduler.py enable` | Re-installs cron |
| "Turn off the daily schedule" | update `profile.yml` → run `scheduler.py disable` | Remove cron |
| "Add my Gemini API key [key]" | `config/profile.yml` | Write to `automation.gemini_api_key` |

Pattern: read file → make the minimum change needed → write file → confirm in one sentence.

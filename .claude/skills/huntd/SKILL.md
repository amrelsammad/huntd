# huntd — AI Job Hunting Assistant

Use this skill when the user says `/huntd`, "scan for jobs", "score jobs", "push to notion", "job hunting", or "check job pipeline".

## On every `/huntd` command — run the update check first

Before executing any command below, run:
```
uv run python scripts/check_update.py
```
If it prints an update notice, show it to the user before proceeding. If it produces no output, continue silently.

---

## Commands

### `/huntd scan`
Run the ATS scraper and search queries to discover new jobs.

Steps:
1. Run the update check (see above)
2. Run: `uv run python scripts/scan.py`
   This fetches jobs from `tracked_companies` (Greenhouse, Lever, Ashby, SmartRecruiters, Workable) and adds new ones to `data/pipeline.md`.
3. Read `config/portals.yml` → `search_queries` section. If present and non-empty:
   For each query string:
   a. Run WebSearch with that query
   b. For each result that looks like a job posting (has a clear title, company name, and direct job URL):
      - Extract: URL, job title, company name (from snippet or domain), location (from snippet or "Unknown")
      - Infer Source from the URL domain: bayt.com → "Bayt", gulftalent.com → "GulfTalent", linkedin.com → "LinkedIn"
      - Skip if URL is already in `data/seen.json`
      - Append to `data/pipeline.md`: `- [ ] {url} | {company} | {title} | {location}`
      - Add URL to `data/seen.json`
   c. Be selective: only add URLs that are clearly individual job postings — skip company career pages, search results pages, or category listings
4. Report: X jobs from ATS scrapers, Y jobs from search queries
5. Suggest: "Run `/huntd score` to score the new jobs."

### `/huntd score`
Score pending jobs against the candidate profile.

Steps:
1. Run the update check (see above)
2. Read `modes/_shared.md` (system context and data formats)
3. Follow `modes/score.md` exactly
4. Score all `- [ ]` entries in `data/pipeline.md`
5. Write scored jobs to `data/scored.md`
6. Mark scored entries as `- [x]` in `data/pipeline.md`
7. Report summary (counts + top matches)

### `/huntd push`
Push scored jobs to Notion.

Steps:
1. Run the update check (see above)
2. Run: `uv run python scripts/push_notion.py`
3. Report: how many jobs were pushed, any failures
4. If Notion credentials are invalid, explain where to set them (`config/profile.yml`)

### `/huntd push --dry-run`
Preview what would be pushed without actually pushing.

Steps:
1. Run: `uv run python scripts/push_notion.py --dry-run`
2. Show the preview output

### `/huntd push --obsidian`
Push scored jobs as local Obsidian markdown notes.

Steps:
1. Run the update check (see above)
2. Run: `uv run python scripts/push_obsidian.py`
3. Report: how many notes were written and to which folder
4. If `obsidian.vault_path` is not set, tell the user: "Tell me your Obsidian vault path and I'll set it — e.g. 'set my Obsidian vault path to /home/user/MyVault'"

### `/huntd push --obsidian --dry-run`
Preview Obsidian notes without writing any files.

Steps:
1. Run: `uv run python scripts/push_obsidian.py --dry-run`
2. Show the preview table

### `/huntd status`
Show pipeline stats.

Steps:
1. Read `data/pipeline.md`
2. Count: total lines, `- [ ]` (pending), `- [x]` (scored)
3. Read `data/scored.md`
4. Count: total scored entries, by score bucket (1-3, 4-6, 7-10)
5. Report summary table

### `/huntd update`
Pull the latest changes from the remote repo and reinstall dependencies.

Steps:
1. Run: `git pull`
2. Run: `uv sync`
3. Report what changed (show git pull output summary)
4. Confirm: "huntd is up to date."

If `git pull` fails (e.g., local changes conflict), show the error and tell the user: "There are local changes that conflict with the update. You can stash them with `git stash`, then re-run `/huntd update`."

### `/huntd schedule`
Enable, disable, change, or check the daily automated pipeline.

Steps:
1. **Enable** (`/huntd schedule enable` or "enable the daily pipeline"):
   - Ask: "What time would you like the daily run? (default: 9:00 PM)"
   - Write the chosen time to `config/profile.yml` → `schedule.time`
   - Set `schedule.enabled: true` in profile.yml
   - Run: `uv run python scripts/scheduler.py enable`
   - Check `config/profile.yml` for `automation.gemini_api_key` — if empty, warn: "Automated scoring needs a free Gemini API key. Get one at aistudio.google.com and tell me 'add my Gemini API key [key]'. Without it, the daily run will scan and push but skip scoring."
2. **Disable** (`/huntd schedule disable` or "turn off the schedule"):
   - Set `schedule.enabled: false` in profile.yml
   - Run: `uv run python scripts/scheduler.py disable`
3. **Change time** ("change my schedule to 8 AM" / "move it to 7:30 PM"):
   - Update `schedule.time` in `config/profile.yml`
   - Run: `uv run python scripts/scheduler.py enable` (re-installs cron with new time, replaces old entry)
   - Confirm: "Daily pipeline now runs at [new time]."
4. **Status** (`/huntd schedule status` or "when does huntd run?"):
   - Run: `uv run python scripts/scheduler.py status`
   - Also read `config/profile.yml` to show configured time vs. actual cron entry

### `/huntd setup`
First-run setup: get the resume path from the user → parse it → auto-generate profile and company list. Never ask the user to paste or edit files.

Steps:
1. Ask the user to drag their resume file (PDF or DOCX) into the terminal window. Explain: "Drag your resume file from Finder into this terminal — it will paste the file path. Then press Enter." Wait for them to paste the path.
   - If `resume.md` already exists with real content (not the placeholder), skip this step and read it directly.
   - If the user provides no path and `resume.md` is empty/placeholder, prompt once more then stop with: "Please drag your resume (PDF or DOCX) into the terminal to continue setup."
2. Run: `uv run python scripts/parse_resume.py [the pasted path]`
   - This parses the resume into `resume.md`.
   - Show any output from the script.
3. Read `resume.md` in full.
4. Extract from the resume:
   - Current/most recent job title → infer target roles (e.g., "Senior PM" → targets: Senior PM, Lead PM, Head of Product)
   - Years of experience → infer seniority level
   - Industries worked in → infer target industries
   - Skills and domain expertise → used for scoring weights
   - Location (if mentioned) → infer preferred work locations
5. Generate and write `config/profile.yml` using the extracted info. Use `config/profile.example.yml` as the schema template.
6. Generate and write `config/portals.yml`:
   - Detect the candidate's location from the resume (city, country, address, or current company HQ).
   - If location signals UAE, Dubai, Abu Dhabi, Saudi Arabia, Riyadh, KSA, or GCC:
     • `tracked_companies`: use MENA companies from `portals.example.yml` (Careem, Tamara, Delivery Hero)
     • `search_queries`: Bayt/GulfTalent/LinkedIn queries using candidate's target role + UAE/KSA cities
   - If location signals US, Canada, UK, or Europe:
     • `tracked_companies`: US/Global companies from `portals.example.yml`
     • `search_queries`: LinkedIn queries with target role + US/EU region
   - If location is ambiguous or remote: include mix from both regions
   - Always include 6-10 `tracked_companies` and 4-6 `search_queries` tailored to the candidate's target roles
   - Use `config/portals.example.yml` as the schema template.
7. Generate and write `modes/_profile.md`: infer archetypes, deal-breakers, and scoring notes from the resume. Use `modes/_profile.template.md` as the template.
8. Ask for the Notion token and database ID (the only things that cannot be inferred from the resume). Write them into `config/profile.yml`.
9. Ask: "Would you like to enable the daily automated pipeline? It will scan, score, and push new jobs to Notion every day. If yes — what time works best?"
   - If yes: ask for preferred time (e.g., "9 PM", "8 AM") → write to `profile.yml` `schedule.time` → run `uv run python scripts/scheduler.py enable`
   - If no: leave `schedule.enabled: false` in profile.yml
   - Regardless: remind the user that automated scoring requires a free Gemini API key — if they haven't provided one, note "You can add it later by telling me 'add my Gemini API key'."
10. Run: `uv sync`
11. Confirm with a summary: "Setup complete. Here's what I created: [list target roles, industries, companies, Notion status, schedule status]. To update anything, just tell me — for example: 'Add Stripe to my tracked companies', 'Change my schedule to 7 AM', or 'I'm also open to Director-level roles'."
12. Suggest: "Run `/huntd scan` to discover your first jobs."

### Profile and company updates (conversational)
When the user asks to update their profile or companies (e.g., "add Figma", "remove fintech", "I want remote-only"):
1. Read the relevant config file (`config/portals.yml` or `config/profile.yml` or `modes/_profile.md`)
2. Make the change
3. Write the file back
4. Confirm: "Done — [describe exactly what changed]"

#### Auto-detecting ATS when adding a company

When the user says "Add [Company] to my tracked companies" and the ATS is not known:

1. Derive a slug: lowercase the company name, remove spaces and special characters (e.g., "Property Finder" → `propertyfinder`, "stc pay" → `stcpay`)
2. Try each ATS in order using `uv run python -c`:
   ```python
   import requests
   slug = "SLUG_HERE"
   tests = [
       ("greenhouse", f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", lambda r: len(r.json().get("jobs", [])) > 0),
       ("ashby",      f"https://api.ashbyhq.com/posting-api/job-board/{slug}",   lambda r: len(r.json().get("jobs", [])) >= 0 and r.status_code == 200),
       ("lever",      f"https://api.lever.co/v0/postings/{slug}",                lambda r: isinstance(r.json(), list)),
       ("smartrecruiters", f"https://api.smartrecruiters.com/v1/companies/{slug}/postings", lambda r: r.json().get("totalFound", 0) > 0),
   ]
   for ats, url, check in tests:
       try:
           r = requests.get(url, timeout=6)
           if r.ok and check(r):
               print(f"FOUND:{ats}")
               break
       except Exception:
           pass
   else:
       print("NOT_FOUND")
   ```
3. If `FOUND:{ats}` — add the entry to `config/portals.yml` with the detected ATS and `enabled: true`
4. If `NOT_FOUND` — tell the user: "I couldn't auto-detect [Company]'s ATS. Share their careers page URL and I'll add it manually."

---

## Important rules

- **Never apply to jobs automatically**
- **Never customize resumes per job** (out of scope for this tool)
- **Never ask the user to edit YAML or markdown files directly** — make changes on their behalf
- **Always read `modes/_shared.md` before scoring** (defines data formats)
- **Always read `resume.md` before scoring** (never score without it)

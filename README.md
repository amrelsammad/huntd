# /huntd

**Free, open source AI-powered job hunting automation for your job search.**

/huntd scans ATS job boards (Greenhouse, Ashby, Lever, SmartRecruiters, Workable), scores each opening against your resume using your AI CLI (Claude Code, Codex, Gemini), and pushes the best matches to a the /huntd Notion database — automatically, every day. No more per-job API costs.
---
## What you need before starting

- A **Notion** account (free — [notion.so](https://notion.so))
- An **AI CLI** — Gemini, Claude Code, or Codex (see Step 2)
- **Python 3.10+** and **git**
- Your resume as a **PDF or DOCX** file

---

## Quickstart (Defaulted to Gemini CLI)

```bash
# 1. Clone and install
git clone https://github.com/amrelsammad/huntd.git && cd huntd
curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.zshrc
uv sync

# 2. Run setup — drag your resume into the terminal when prompted
gemini "run /huntd setup"

# 3. Run the pipeline
gemini "run /huntd scan"    # discover jobs
gemini "run /huntd score"   # AI scores each job against your profile
gemini "run /huntd push"    # push top matches to Notion
```

---

## Step 1 — Set up Notion

### Duplicate the template

A ready-made Notion database that your opportunities sits in. Duplicate it into your workspace:

**[→ Open the /huntd Notion template](https://grey-postage-5c4.notion.site/huntd-35b89f7d7a7a8129a6d3c5e1c782355b)**

Click **Duplicate** (top-right) → choose your workspace. Done.

### Create a Notion integration (API key)

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) → **+ New Connection**
2. Name it `/huntd`, select your workspace, click **Submit**
3. Copy the **Internal Integration Token** (starts with `ntn_...`)

### Connect the integration to your database

1. Open the duplicated database in Notion
2. Click **...** menu (top-right) → **Connections** → **Connect to** → select `/huntd`

Without this step, huntd will fail with `401 Unauthorized` when pushing jobs.

### Get your database ID

The ID is the 32-character string in the URL when you open the database:

```
https://www.notion.so/yourworkspace/<THIS-IS-YOUR-DATABASE-ID>?v=...
```

You'll enter both the token and database ID during `/huntd setup`.

---

## Step 2 — Choose your AI CLI

| CLI | Cost |
|-----|------|
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) (Recommended) | **Free** (Google account) |
| [Claude Code](https://www.anthropic.com/claude-code) | Claude subscription |
| [Codex CLI](https://github.com/openai/codex) | Usage-based |

Gemini CLI is recommended if you don't have a subscription — it's free with a Google account and requires no API key for interactive use.

---

## Step 3 — Install huntd

```bash
git clone https://github.com/amrelsammad/huntd.git
cd huntd

# Install uv (fast Python package manager — run once)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc        # or restart your terminal

# Install dependencies
uv sync
```

> **Windows:** use `irm https://astral.sh/uv/install.ps1 | iex` in PowerShell to install uv.

---

## Step 4 — First-time setup

Run from inside the `/huntd` directory:

```bash
gemini "run /huntd setup"   # Gemini CLI
# or: claude → /huntd setup  (Claude Code)
# or: codex "run /huntd setup"  (Codex)
```

Setup will:
1. Ask you to **drag your resume** (PDF or DOCX) into the terminal — pastes the file path, huntd reads and parses it
2. Auto-generate your scoring profile, target company list, and deal-breakers from your resume
3. Ask for your Notion token and database ID, then save them
4. Optionally enable the daily automated pipeline


---

## Running the pipeline

```bash
/huntd scan     # fetch new jobs from ATS boards + site-filtered web searches
/huntd score    # AI reads each JD, scores 1-10 with fit reasons + red flags
/huntd push     # send scored jobs to your Notion database
```

Run them in sequence. Results flow directly to Notion.

---

## All commands

| Command | What it does |
|---------|-------------|
| `/huntd setup` | First-run: parse resume → generate profile, company list, scoring config |
| `/huntd scan` | Fetch new jobs from ATS APIs + web searches → `data/pipeline.md` |
| `/huntd score` | AI scores all pending jobs → `data/scored.md` |
| `/huntd push` | Push scored jobs to Notion |
| `/huntd push --dry-run` | Preview what would be pushed, without sending anything |
| `/huntd status` | Show pipeline stats: pending, scored, score distribution |
| `/huntd update` | Pull latest huntd changes from GitHub + reinstall dependencies |
| `/huntd schedule enable` | Install a daily cron (scan → score → push) |
| `/huntd schedule disable` | Remove the daily cron |
| `/huntd schedule status` | Show whether the schedule is active and at what time |

---

## Supported platforms

### ATS job boards

| Platform | Example companies |
|----------|-----------------|
| **Greenhouse** | Careem, Tamara, OKX, Stripe, ai71 |
| **Ashby** | Deliveroo UAE, Lean Technologies |
| **SmartRecruiters** | Talabat (Delivery Hero), Roland Berger, Masdar |
| **Workable** | Foodics, Salla |
| **Lever** | (add your own — supported but no UAE/KSA examples yet) |

**18 UAE/KSA companies pre-loaded**, all verified. See the file for the full list.

### Job portals (via AI session web search)

`/huntd scan` also runs site-filtered searches during your AI session, covering portals without public APIs:

| Portal | Region | Example query |
|--------|--------|---------------|
| **Bayt** | UAE, KSA, MENA | `site:bayt.com "senior product manager" Dubai` |
| **GulfTalent** | GCC | `site:gulftalent.com "product manager" UAE` |
| **LinkedIn** | Global | `site:linkedin.com/jobs "head of product" Riyadh` |

These run in your interactive session only — the automated daily cron only hits ATS APIs.

---

## Scoring

Each job is scored 1–10 across five dimensions:

| Dimension | Default weight | What the AI checks |
|-----------|---------------|-------------------|
| Role match | 40% | Title and JD vs. your target roles and track record |
| Location match | 20% | Job location vs. your allowed list; remote availability |
| Industry match | 20% | Company industry vs. your target industries |
| Seniority match | 10% | Role level vs. your target seniority |
| Company quality | 10% | Brand, funding stage, culture signals from the JD |



---

## Daily automation

```bash
/huntd schedule enable    # asks for preferred time, default: 9 PM
/huntd schedule disable
/huntd schedule status
```

The daily cron runs scan → score → push automatically.

The daily cron runs without an active AI session, so it needs a free Gemini API key to score jobs automatically. Get one at [AI Studio](https://aistudio.google.com) — no credit card needed. Without it, the daily run will scan and push but skip scoring. Once you have your key, you can tell you AI:  `"Add my Gemini API key YOUR_KEY"`.


---

## Automatic update checks

huntd checks for updates at the start of every session. If your local copy is behind, you'll see:

```
╭─ huntd ────────────────────────────────────────╮
│ 2 updates available. Run /huntd update to get  │
│ the latest features.                           │
╰────────────────────────────────────────────────╯
```

Run `/huntd update` to pull changes and sync dependencies.

---

## Updating your profile

Tell your AI in plain language — no config editing:

| You say | What changes |
|---------|-------------|
| `"Add Talabat to my tracked companies"` | Adds Stripe to `config/portals.yml` |
| `"Remove Stripe"` | Disables the Stripe entry |
| `"I'm also open to Director-level roles"` | Updates target roles in `config/profile.yml` |
| `"Remove fintech from my target industries"` | Updates `config/profile.yml` |
| `"Add Amsterdam as a target location"` | Updates `config/profile.yml` |
| `"Add a Bayt search for PM roles in Dubai"` | Adds a search query to `config/portals.yml` |
| `"Remove all GulfTalent searches"` | Removes GulfTalent entries from `search_queries` |
| `"Make commission-only a deal-breaker"` | Updates `modes/_profile.md` |
| `"Change my schedule to 8 AM"` | Updates schedule and reinstalls cron |
| `"Add my Gemini API key abc123"` | Saves to `config/profile.yml` |

---

## What huntd does NOT do (Yet)

- **Auto-apply to jobs** — huntd suports surfacing opportunities at the moment.
- **Customize your resume or cover letter** — Your resume is used to only generate your profile on huntd.
- **Call any paid AI API during interactive sessions** — all scoring happens inside your existing CLI session. No cost associated.
---

## Roadmap

- [ ] More MENA companies
- [ ] Wuzzuf portal (Egypt)
- [ ] Workday / SAP SuccessFactors / Oracle Cloud HCM providers
- [ ] Multi-resume support (different profiles for different role types)
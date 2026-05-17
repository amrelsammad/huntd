# huntd — Score Command Instructions

When the user runs `/huntd score`, execute these steps in order.

**Output discipline:** Work silently. Do NOT print per-job scoring details, reasoning, or progress updates while processing. The only output before the final Step 3 report is the one confirmation line at the end of Step 1.

---

## Step 1: Load Context

Read these files (in this order):
1. `resume.md` — candidate's full resume
2. `modes/_profile.md` — archetypes, weights, deal-breakers
3. `config/profile.yml` — targets (roles, locations, seniority, weights)
4. `data/pipeline.md` — pending jobs (lines with `- [ ]`)

Confirm (this is the only output before the final report): "Loaded resume, profile, and N pending jobs from pipeline. Scoring silently..."

---

## Step 2: Score All Pending Jobs

**Important: Score every job in memory first. Do NOT write any files until all jobs are scored.**

For each `- [ ]` entry in `data/pipeline.md`, run steps 2a–2e and hold the result in memory:

### 2a. Extract job info
Parse: URL | Company | Title | Location

### 2b. Fetch job description
Use WebFetch on the job URL. Extract:
- Full job description text
- Requirements
- Team context (if available)

If WebFetch fails (404, timeout), continue with title + company + location only. Note "JD not available" in fit reasons.

### 2c. Check deal-breakers (from modes/_profile.md)
If ANY deal-breaker applies:
- Score = 3 (maximum for dismissed jobs)
- Status = Dismissed
- Red Flags = which deal-breaker triggered
- Skip the weighted scoring below

### 2d. Determine Work Type
Read the job description for work arrangement signals:
- "remote", "work from home", "WFH", "fully remote", "100% remote" → **Remote**
- "hybrid", "flexible", "2–3 days", "partial remote" → **Hybrid**
- "on-site", "in-office", "in-person", "office-based", "no remote" → **On-site**
- No clear signal → **Unknown**

Prefer the JD body over the job title. Title says "Remote" but JD says "3 days in office" → Hybrid.

### 2e. Weighted scoring (if no deal-breaker)
Score each dimension against resume.md content:

| Dimension | Weight | Question to ask |
|-----------|--------|----------------|
| Role Match | 40% | Does title/JD match candidate's target roles and track record? |
| Location Match | 20% | Is the location in the allowed list? Is remote allowed? |
| Industry Match | 20% | Is the company's industry in the candidate's target list? |
| Seniority Match | 10% | Does the role level match candidate's target seniority? |
| Company Quality | 10% | Is this a desirable company (brand, funding, culture signals)? |

Use weights from `config/profile.yml` `scoring.weights` if present.

**Score formula:** `total = sum(dimension_score * weight/100)` where each dimension is rated 1-10.

**Soft flags:** For each soft flag (from modes/_profile.md) that applies, subtract 1 from total. Minimum score = 1.

---

After scoring ALL pending jobs, do the two file writes below (once each, not per job):

### 2f. Write ALL scored entries to data/scored.md in one operation
Append all results at once using the exact format from `modes/_shared.md`. Example entry:

```markdown
### Notion — Senior Product Manager
- **URL:** https://boards.greenhouse.io/notion/jobs/123456
- **Score:** 8/10
- **Status:** New
- **Location:** San Francisco, CA
- **Work Type:** Hybrid
- **Source:** Greenhouse
- **Fit Reasons:** • Strong PM role at a product-led B2B SaaS company • Remote-friendly culture • Seniority level aligns with target (Senior PM)
- **Red Flags:** No explicit equity details in JD
```

### 2g. Update data/pipeline.md once
Change all scored `- [ ]` entries to `- [x]` in a single edit.

---

## Step 3: Report

After all jobs are scored, output a summary:

```
## Scoring Complete

- Total scored: N
- Score distribution:
  - 7-10 (strong fit): X jobs
  - 4-6 (possible fit): Y jobs
  - 1-3 (poor fit / dismissed): Z jobs

## Top Matches
1. {Company} — {Title} | Score: {N}/10 | {Location}
2. ...
3. ...

Run `/huntd push` to send scored jobs to Notion.
```

---

## Notes

- **Min score to push:** Check `config/profile.yml` `scoring.min_score_to_push`. Jobs below this score should have Status=Dismissed so push_notion.py can skip them (or the user can filter in Notion).
- **One session, multiple batches:** If there are many pending jobs (>20), ask the user if they want to score all at once or in batches.
- **Scheduled scoring:** The automated daily run uses `scripts/score_batch.py` (Gemini API). This command (`/huntd score`) is the manual, in-session version — it is always more thorough because it uses a full AI session with WebFetch access.

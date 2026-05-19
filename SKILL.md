---
name: chaoxing-assignment-grading
description: "Use when grading Chaoxing/Xuexitong assignments. Teacher workflow: identify course/class/assignment, confirm scoring setup, optionally inspect/export materials, draft scores, and submit only after explicit confirmation."
version: 2.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [chaoxing, xuexitong, grading, education, assignment, automation]
    related_skills: [browser-harness]
---

# Chaoxing Assignment Grading

Use this skill for teacher-side Chaoxing/Xuexitong assignment grading workflows.

## Mandatory Rule Loading

For every run, read `references/agent-rules.md` first. It is the short rule contract and overrides every script example, browser snippet, API snippet, and step guide.

Use `references/workflow-checklist.md` as the live checklist. Use step files only when the current phase needs implementation details.

Scripts are tools, not workflow authority. A command example never grants permission to open submissions, export, download, inspect, import, submit, return work, or otherwise write unless the rules and current teacher confirmation allow that step.

## Script-First Discovery

For read-only orientation, use the stable scripts before agent/browser exploration:

1. Check saved cookies with `scripts/check_cookie.py`.
2. If needed, log in with `scripts/chaoxing_login_cookie.py`.
3. Discover teacher courses, matching classes, assignments, and counts with `scripts/chaoxing_discover.py`.
4. Use browser DOM exploration only when the discovery script fails or the page structure has changed. If a fallback is needed, report the failure and the fallback evidence.

The discovery script is allowed only for Step 1 orientation. It must not open individual student submissions, export/download materials, draft scores, or write grades.

## Cookie And Session Reality Check

Treat the browser session and the script/API cookie session as separate state. A Chaoxing page opened in the browser may redirect to the login page while the local MozillaCookieJar file still works for scripts and API calls. Do not conclude that the script session is expired from the browser redirect alone; verify with `scripts/check_cookie.py` against the cookie file and report both facts when they disagree.

Use the skill directory as the default working directory and keep the cookie file at the relative path `./cx_cookies.txt`. This relative path is the cross-platform contract for Linux, macOS, and Windows. Run scripts from the skill directory or pass `--cookie-file ./cx_cookies.txt` explicitly. If a previous run saved cookies elsewhere, use the platform's normal file search only to migrate or copy it back into the skill directory; do not make environment-specific absolute paths part of the normal workflow.

## Non-Negotiable Safety Rule

You may inspect pages, open previews, download/export attachments, parse documents, and draft score suggestions only within the confirmed scoring mode.

Before changing grades, comments, plagiarism markers, return status, or clicking `提交`, `提交并进入下一份`, `完成`, or `打回重做`, show the exact planned action and wait for explicit teacher confirmation in the current turn.

## State Machine

Keep every run in this explicit order:

1. **Orient**: identify the course, class, assignment, submitted count, unsubmitted count, and current page URL.
2. **Confirm scoring setup**: before opening submissions, exporting, packaging, downloading, extracting, or parsing assignment files, ask the teacher to confirm score range and scoring mode.
3. **Prepare evidence according to mode**:
   - `random`: do not open, export, download, extract, parse, or inspect assignment files.
   - `concise`: use exported metadata and metrics as rough evidence; inspect flagged cases only.
   - `detailed`: inspect every available assignment file before scoring.
4. **Draft scores**: produce the fixed score draft schema with evidence.
5. **Preflight write**: show exact target, score list, write method, unsubmitted count, and manual-review count.
6. **Confirm write**: write only after explicit current-turn teacher confirmation of that exact final plan.
7. **Verify**: re-open the list and download the exported grade table, compare the exact submitted scores, and report mismatches.

Required ledger:

```text
course: <name> | courseid=<id>
class: <name> | clazzid=<id>
assignment: <title> | workId=<id>
counts: submitted=<n> pending_review=<n> unsubmitted=<n>
score_range: <min>-<max> | confirmed=<yes/no>
scoring_mode: random | concise | detailed | confirmed=<yes/no>
method: read-only | list-input | export-edit-import | individual-submit
verification: mark-list | exported-grade-table | both
write_allowed: no until explicit teacher confirmation
```

## Step Guides

Read only the guide for the current phase:

- `references/steps/01-login.md`: login, cookie checks, and cookie injection.
- `references/steps/02-course-assignment.md`: course, class, assignment, and review-list discovery.
- `references/steps/03-scoring-setup.md`: score range and scoring mode confirmation.
- `references/steps/04-materials.md`: export, download, extract, and material metadata preparation.
- `references/steps/05-draft-scores.md`: random, concise, and detailed score drafting.
- `references/steps/06-submit-verify.md`: dry-run, preflight, confirmed submission/import, and verification.

Supporting references:

- `references/agent-rules.md`: mandatory short rules.
- `references/workflow-checklist.md`: run checklist.
- `references/scoring-methodology.md`: scoring bands and concise-mode methodology.
- `references/script-usage.md`: script command cookbook.
- `references/browser-harness-fallback.md`: Browser harness fallback map when a script fails or page/API structure changes.
- `references/playwright-submit-fallback.md`: fallback submission approach.
- `references/full-workflow-legacy.md`: archived long workflow with older page/API details.

## Output Contracts

Teacher-facing score drafts and write confirmations must use concise Chinese Markdown tables, not raw CSV. Keep raw metrics and CSV rows for machine scripts, saved artifacts, or teacher-requested audit details.

Calibration table for `concise` or `detailed` modes:

```text
student_id | student_name | chars | images | sections | key_requirement | status | provisional_band | notes
```

Score draft schema:

```csv
student_id,student_name,score,band,evidence,penalty_reason,needs_manual_review,workAnswerId
```

Every score must be inside the teacher-confirmed score range. In `random` mode, evidence must state `teacher-selected random scoring; assignment not inspected`.

## Pitfalls

- Browser login state and script cookie state can disagree; a browser redirect to login does not invalidate a separately stored cookie file by itself.
- Keep `cx_cookies.txt` in the skill directory as `./cx_cookies.txt`; avoid baking environment-specific absolute paths into commands or reports.
- Do not download or inspect assignment files before score range and mode are confirmed.
- Do not use XLS import when unsubmitted rows are present unless they are removed and the exact import plan is confirmed.
- Do not treat `batch_grade.py` metrics as final grades by themselves.
- Do not claim content quality in `random` mode.
- Do not submit scores until the teacher has seen the exact score list and explicitly confirmed it.
- Do not commit cookies, downloaded student submissions, generated reports, or score CSVs containing student data unless explicitly requested.

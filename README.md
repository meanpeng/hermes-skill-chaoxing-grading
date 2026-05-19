# chaoxing-assignment-grading

Chaoxing/Xuexitong teacher-side assignment grading helper for Codex/AI agents.

This skill helps agents safely:

- discover courses, classes, assignments, and pending counts
- download/export assignment packages after scoring mode is confirmed
- prepare local report metadata for grading
- draft score tables for teacher review
- submit scores only after explicit teacher confirmation
- verify written scores from Chaoxing's exported grade table

## Safety

Never write grades automatically. Any action that changes scores, comments, return status, or clicks final submit must wait until the teacher has seen the exact target and score list and confirms that exact plan in the current turn.

`random` mode must not inspect submissions. `concise` and `detailed` modes may access materials only after the teacher confirms the score range and scoring mode.

Cookies, downloaded student submissions, generated grading CSVs, and score reports are local private data. Do not commit them unless explicitly requested.

## Install

Install Python dependencies from `requirements.txt` before using the local scripts. Use the repo root as the working directory and keep Chaoxing cookies at `./cx_cookies.txt`.

## Core Workflow

1. **Login / cookie check**

   Establish or verify the local Chaoxing cookie session.

2. **Read-only discovery**

   Discovery is read-only. It should identify the target course, class, assignment, `workId`, submitted count, pending-review count, and unsubmitted count.

3. **Confirm scoring setup**

   Before opening, exporting, downloading, or parsing submissions, ask the teacher for:

   ```text
   score_range: <min>-<max>
   scoring_mode: random | concise | detailed
   ```

4. **Prepare materials**

   Only for confirmed `concise` or `detailed` mode. Material preparation creates local metadata and reports; it does not grade.

5. **Draft scores**

   Use `references/scoring-methodology.md` and `references/steps/05-draft-scores.md`. Teacher-facing drafts should be concise Chinese Markdown tables, not raw CSV.

   If a row is `unreadable`, the agent must inspect that student's local candidate files directly before asking the teacher to review. Rerunning a material-prep script is not enough.

6. **Submit and verify**

   Dry-run first. Add the write confirmation flag only after the teacher confirms the exact final score list. After writing, verify against Chaoxing's exported grade table.

## Important References

- `SKILL.md`: skill entrypoint and state machine
- `references/agent-rules.md`: mandatory short rule contract
- `references/workflow-checklist.md`: live ledger and verification checklist
- `references/steps/`: phase-specific templates and details
- `references/scoring-methodology.md`: concise/detailed scoring guidance
- `references/script-usage.md`: command cookbook
- `references/browser-harness-fallback.md`: fallback browser procedures
- `references/playwright-submit-fallback.md`: fallback submit procedure
- `references/full-workflow-legacy.md`: archived older API/page notes

## Scripts

- `scripts/check_cookie.py`: verify saved cookie session
- `scripts/chaoxing_login_cookie.py`: login and save cookies
- `scripts/chaoxing_discover.py`: read-only course/class/assignment discovery
- `scripts/download_work_zips.py`: dry-run-first package downloader
- `scripts/prepare_work_materials.py`: extract zips and prepare material reports
- `scripts/extract_work_zip.py`: safe zip extractor
- `scripts/batch_grade.py`: material/metric CSV generator
- `scripts/submit_scores.py`: dry-run-first list-page score writer
- `scripts/verify_score_export.py`: exported-grade verification
- `scripts/batch_submit_scores.py`: legacy individual-page submit helper

## License

MIT

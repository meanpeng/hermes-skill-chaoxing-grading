# Agent Rules

This file is the mandatory short rule contract for every model. Follow it before reading script examples or page-specific cookbook notes.

## Priority

Rules in this file override script examples, browser snippets, and API snippets. Scripts are tools only; they do not grant permission to proceed.

## Required State

Maintain this ledger during every run:

```text
course: <name> | courseid=<id>
class: <name> | clazzid=<id>
task: assignment <title> | workId=<id>
task: exam <title> | relationid=<id> | paperId=<id>
counts: submitted=<n> pending_review=<n> unsubmitted=<n>
score_range: <min>-<max> | confirmed=<yes/no>
scoring_mode: random | concise | detailed | confirmed=<yes/no>
verification: mark-list | exported-grade-table | both
write_allowed: no until teacher confirms exact final write plan
```

If a required field is unknown, collect it before moving to the next phase.

## Gates

1. Identify the target course, class, task type, task title, and counts. When listing class tasks, list both assignments and exams.
   - If a teacher-provided task name matches both an assignment and an exam, ask the teacher to choose the task type before continuing.
2. Before opening, exporting, downloading, extracting, or parsing assignment files, ask the teacher to confirm:
   - score range
   - scoring mode: `random`, `concise`, or `detailed`
   When the course/class/assignment context is Chinese, use the Chinese scoring setup template in `references/steps/03-scoring-setup.md` so the teacher supplies both fields explicitly.
3. If mode is `random`, do not download, open, export, extract, or parse assignment files. Use only the student list/IDs and label evidence as `teacher-selected random scoring; assignment not inspected`.
4. If mode is `concise`, use metadata and metrics only as rough evidence. Inspect flagged or ambiguous cases.
   - `unreadable` is an agent action item, not a teacher action item. Before listing it as needing teacher review, the agent must personally inspect the student's local files and available alternatives: open another report candidate in the student's folder, inspect nested archives/attachments, examine the file with an appropriate reader or extractor, and use a downloaded PDF/original-attachment package if available or safely obtainable under the confirmed mode.
   - Do not treat rerunning the material-prep script as the confirmation step. Scripts may locate files, but the confirmation is the agent's direct inspection of the candidate files. Only mark an `unreadable` submission for teacher review after direct inspection attempts fail, and report which files/alternatives were inspected.
5. If mode is `detailed`, inspect every available assignment file before scoring.
   - For exams, `detailed` is the only allowed mode. Do not use `random` or `concise` scoring for exams. Export the complete Word answer record and inspect every submitted student's subjective answers before drafting totals.
6. Before writing scores, show the exact score list, target course/class/assignment, write method, unsubmitted count, and remaining manual-review count.
7. Write only after the teacher explicitly confirms that exact final write plan in the current turn.
8. After writing, verify by re-opening the list and downloading the exported grade table. Treat the exported grade table as the final independent verification source when it is available.

## Never

- Never submit scores, import score files, return work, change comments, or click final submit buttons without explicit current-turn teacher confirmation.
- Never use XLS import when unsubmitted rows are present unless they are removed and the teacher has confirmed the exact import plan.
- Never invent content-based evidence in `random` mode.
- Never treat `batch_grade.py` metrics as final grades by themselves.
- Never commit cookies, student submissions, generated score CSVs, or private grading artifacts unless explicitly requested.

## Required Score Draft Schema

For teacher-facing messages, show score drafts and write confirmations as concise Markdown tables in Chinese. Do not paste raw CSV or raw metric strings as the default response. Convert evidence into short human-readable reasons, and include detailed metrics or CSV only when the teacher asks for audit/source data.

```csv
student_id,student_name,score,band,evidence,penalty_reason,needs_manual_review,workAnswerId
```

Every score must be inside the confirmed score range.

# Agent Rules

This file is the mandatory short rule contract for every model. Follow it before reading script examples or page-specific cookbook notes.

## Priority

Rules in this file override script examples, browser snippets, and API snippets. Scripts are tools only; they do not grant permission to proceed.

## Required State

Maintain this ledger during every run:

```text
course: <name> | courseid=<id>
class: <name> | clazzid=<id>
assignment: <title> | workId=<id>
counts: submitted=<n> pending_review=<n> unsubmitted=<n>
score_range: <min>-<max> | confirmed=<yes/no>
scoring_mode: random | concise | detailed | confirmed=<yes/no>
verification: mark-list | exported-grade-table | both
write_allowed: no until teacher confirms exact final write plan
```

If a required field is unknown, collect it before moving to the next phase.

## Gates

1. Identify the target course, class, assignment, and counts.
2. Before opening, exporting, downloading, extracting, or parsing assignment files, ask the teacher to confirm:
   - score range
   - scoring mode: `random`, `concise`, or `detailed`
3. If mode is `random`, do not download, open, export, extract, or parse assignment files. Use only the student list/IDs and label evidence as `teacher-selected random scoring; assignment not inspected`.
4. If mode is `concise`, use metadata and metrics only as rough evidence. Inspect flagged or ambiguous cases.
5. If mode is `detailed`, inspect every available assignment file before scoring.
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

```csv
student_id,student_name,score,band,evidence,penalty_reason,needs_manual_review,workAnswerId
```

Every score must be inside the confirmed score range.

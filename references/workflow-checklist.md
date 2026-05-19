# Model-Stable Workflow Checklist

Use this checklist when a model is likely to skip steps, over-trust metrics, or rush to browser writes.

## 1. Context Ledger

Fill this before exporting, grading, or submitting:

```text
course: <name> | courseid=<id>
class: <name> | clazzid=<id>
assignment: <title> | workId=<id>
page_url: <url>
submitted: <n>
pending_review: <n>
unsubmitted: <n>
cookie_checked: yes/no
```

If the class, assignment, or counts are uncertain, stop and collect them.

## 2. Scoring Setup Gate

Confirm these before opening student submissions, exporting, downloading, extracting, or parsing files:

```text
score_range: <min>-<max>
scoring_mode: random | concise | detailed
setup_confirmed_by_teacher: yes/no
```

Allowed modes:

- `random`: random scoring inside the confirmed range. Do not download, open, or inspect assignment files. Evidence must say assignment content was not inspected.
- `concise`: rough scoring from metadata such as text length, section/key-requirement signals, image count, and previews.
- `detailed`: open every student's assignment file and inspect actual content before scoring.

If `setup_confirmed_by_teacher` is not `yes`, do not continue.

## 3. Read-Only Material Prep

Use this only for `concise` or `detailed` mode. Skip it entirely for `random` mode.

Safest sequence:

```bash
python scripts/extract_work_zip.py output.zip -d output_dir
python scripts/batch_grade.py --base-dir output_dir --mode materials
python scripts/batch_grade.py --base-dir output_dir --mode metrics --sample 5
```

Metrics are reading aids. They are not grades.

## 4. Calibration Gate

Use this only for `concise` or `detailed` mode. Skip submission-based calibration for `random` mode.

Purpose: use the sample to calibrate the grading posture before full drafting. The sample should help estimate the assignment quality distribution, catch cases where metrics are misleading, align lenient/strict/custom teacher expectations, and keep later full-batch scoring consistent. Do not treat sample rows as final scores until the full draft is produced and reviewed.

Show 3-5 representative submissions:

```text
student_id | student_name | chars | images | sections | key_requirement | status | provisional_band | notes
```

Ask the teacher to accept or adjust one grading posture:

- lenient homework posture
- strict assessment posture
- custom teacher rubric

Do not produce a full write plan until this gate is passed.

## 5. Score Draft Schema

Keep teacher-facing output separate from machine input. Show the teacher a Chinese Markdown table:

```text
| 学号 | 姓名 | 分数 | 档位 | 建议复核 | 说明 |
|---|---|---:|---|---|---|
```

Use short Chinese reasons in `说明`; do not paste raw `metrics: chars=..., images=...` strings in the main response.

Use this exact CSV schema only for scripts or saved artifacts:

```csv
student_id,student_name,score,band,evidence,penalty_reason,needs_manual_review,workAnswerId
```

For `unreadable` rows, first perform agent-side direct confirmation before assigning teacher-facing review:
open and inspect alternate report candidates, nested archives/attachments, and any already downloaded PDF/original-attachment package. If the confirmed scoring mode allows it and the package is not already available, safely obtain the alternate package before asking the teacher to review. Rerunning the material-prep script is not sufficient confirmation; it can only help locate files.

Set `needs_manual_review=true` only for unresolved unreadable rows after direct agent inspection fails, or for missing, suspicious, mismatched, or image-heavy submissions that have not been visually inspected.

Every score must be inside the confirmed score range. In `random` mode, do not invent content-based evidence.

## 6. Write Preflight

Before writing scores, show:

```text
method: list-input | export-edit-import | individual-submit
scoring_mode: random | concise | detailed
score_range: <min>-<max>
target course/class/assignment: <values>
student_count_to_write: <n>
expected_submitted_count: <n>
mark_pages_expected: <n|auto>
mark_rows_collected: <n>
manual_review_remaining: <n>
unsubmitted_count: <n>
teacher_confirmed_exact_score_list: yes/no
```

The only valid state for writing is `teacher_confirmed_exact_score_list: yes`.

If `mark_rows_collected` is lower than `expected_submitted_count`, the mark list is incomplete. For counts above 20, assume pagination first and collect additional review-list pages before matching or writing scores.

## 7. Post-Write Verification

After writing, verify twice when possible:

1. Re-open or refetch the mark list to catch immediate API failures.
2. Download the exported grade table and compare the target rows against the expected score list.

```text
verification_source: mark-list | exported-grade-table | both
expected_written: <n>
verified_written: <n>
mismatches: <student ids or none>
status_regressions: <unsubmitted/redo/completed anomalies or none>
```

Report mismatches before doing any recovery action.

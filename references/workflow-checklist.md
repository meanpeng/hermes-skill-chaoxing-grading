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
- `concise`: rough scoring from metadata such as text length, section/reflection signals, image count, and previews.
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

Show 3-5 representative submissions:

```text
student_id | student_name | chars | images | sections | reflection | status | provisional_band | notes
```

Ask the teacher to accept or adjust one grading posture:

- lenient homework posture
- strict assessment posture
- custom teacher rubric

Do not produce a full write plan until this gate is passed.

## 5. Score Draft Schema

Use this exact schema:

```csv
student_id,student_name,score,band,evidence,penalty_reason,needs_manual_review,workAnswerId
```

Set `needs_manual_review=true` for unreadable, missing, suspicious, mismatched, or image-heavy submissions that have not been visually inspected.

Every score must be inside the confirmed score range. In `random` mode, do not invent content-based evidence.

## 6. Write Preflight

Before writing scores, show:

```text
method: list-input | export-edit-import | individual-submit
scoring_mode: random | concise | detailed
score_range: <min>-<max>
target course/class/assignment: <values>
student_count_to_write: <n>
manual_review_remaining: <n>
unsubmitted_count: <n>
teacher_confirmed_exact_score_list: yes/no
```

The only valid state for writing is `teacher_confirmed_exact_score_list: yes`.

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

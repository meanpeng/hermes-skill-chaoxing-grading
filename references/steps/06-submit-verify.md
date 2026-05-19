# Step 06: Submit And Verify

Read `references/agent-rules.md` first. This step can write grades and therefore requires explicit current-turn teacher confirmation of the exact final write plan.

## Write Preflight

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

The only valid write state is `teacher_confirmed_exact_score_list: yes`.

## Dry-Run Individual Submission Helper

```bash
python scripts/batch_submit_scores.py \
  --courseid COURSEID \
  --clazzid CLAZZID \
  --work-id WORK_ID \
  --scores-csv scores.csv
```

Show the dry-run list to the teacher.

Only after explicit confirmation:

```bash
python scripts/batch_submit_scores.py \
  --courseid COURSEID \
  --clazzid CLAZZID \
  --work-id WORK_ID \
  --scores-csv scores.csv \
  --confirm-submit
```

## List Page Direct Input

The review list page has score textboxes such as `input.scoreInput`. Typing a score and blurring the input calls the same API used by `scripts/submit_scores.py`.

Prefer the dry-run-first script instead of browser clicking:

```bash
python scripts/submit_scores.py \
  --cookie-file cx_cookies.txt \
  --courseid COURSEID \
  --clazzid CLAZZID \
  --cpi CPI \
  --work-id WORK_ID \
  --scores-csv final_scores.csv \
  --method list-input
```

The script fetches `/mooc2-ans/work/mark-list`, matches `student_id` or `workAnswerId`, validates the exact target rows, and prints the write plan. It does not write unless `--confirm-submit` is passed after teacher confirmation:

```bash
python scripts/submit_scores.py \
  --cookie-file cx_cookies.txt \
  --courseid COURSEID \
  --clazzid CLAZZID \
  --cpi CPI \
  --work-id WORK_ID \
  --scores-csv final_scores.csv \
  --method list-input \
  --confirm-submit
```

Confirmed `list-input` writes call `/mooc2-ans/work/markscore` with one `workAnswerId` at a time. Use only after the write preflight is confirmed.

## XLS Export/Edit/Import

Use only when all students are submitted, or unsubmitted rows have been removed and the teacher has confirmed the exact import plan.

Mandatory import preflight:

```text
all_students_submitted: yes/no
unsubmitted_rows_removed: yes/no/not-applicable
export_enc_collected: yes/no
import_enc_collected: yes/no
modified_file_saved_as_xlsx_then_copied_to_xls: yes/no
teacher_confirmed_exact_score_list: yes/no
```

If any answer is `no`, do not import. Use list-page direct input or stay in draft mode.

## Verify

After writing, use a two-source verification loop when possible:

1. Re-open or refetch the mark list to confirm the list page sees the new score.
2. Download the exported grade table and compare the exported score/status rows against the submitted CSV.

Preferred exported-table verification:

```bash
python scripts/verify_score_export.py \
  --cookie-file cx_cookies.txt \
  --courseid COURSEID \
  --clazzid CLAZZID \
  --cpi CPI \
  --work-id WORK_ID \
  --scores-csv final_scores.csv
```

The script fetches the review page, reads `workScoreExportEnc`, downloads `/import-export-ans/export-workscore`, parses the exported workbook in memory, and compares column A `学号`, B `姓名`, I `分数`, and J `状态` for the submitted targets. Use `--output-file` only when the teacher explicitly wants to keep the downloaded grade table.

```text
verification_source: mark-list | exported-grade-table | both
expected_written: <n>
verified_written: <n>
mismatches: <student ids or none>
status_regressions: <unsubmitted/redo/completed anomalies or none>
```

Report mismatches before retrying or recovering.

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

Chinese write-preflight template:

```text
提交前确认：

目标：
课程：<course> | courseid=<courseid>
班级：<class> | clazzid=<clazzid>
作业：<assignment> | workId=<workId>

评分设置：
评分范围：<score_range>
评分模式：<random|concise|detailed>
写入方式：<list-input|export-edit-import|individual-submit>

写入计划：
待写入人数：<student_count_to_write>
未交人数：<unsubmitted_count>
建议人工复核：<manual_review_remaining>

即将写入的分数：
| 学号 | 姓名 | 分数 | workAnswerId |
|---|---|---:|---|
| <student_id> | <student_name> | <score> | <workAnswerId> |

请明确回复“确认写入以上分数”，我才会提交到超星系统。
```

Use the Markdown table above for the teacher-facing confirmation. Keep the CSV file/schema for scripts, but do not paste raw CSV as the default confirmation message unless the teacher explicitly asks for CSV.

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

The script fetches `/mooc2-ans/work/mark-list`, matches `student_id` or `workAnswerId`, validates the exact target rows, and prints the write plan. If `workinfo` or discovery says there are more submitted rows than one page can contain, treat the list as paged and collect pages until the fetched submitted row count reaches the expected submitted count. For example, 33 submitted rows means at least two mark-list pages must be considered before deciding rows are missing. Use `--mark-pages N` to force a known page count when the page count is already visible. It does not write unless `--confirm-submit` is passed after teacher confirmation:

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

If the script reports fewer `mark_rows` than the expected submitted count, do not guess that the unmatched students are absent or unsubmitted. First inspect `mark_page_stats`: each requested page should add new rows. If page 2 repeats page 1, use the browser review-list DOM pagination or exported grade table to fill the missing `workAnswerId` values before writing.

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

Chinese verification report template:

```text
写入后验证结果：

验证来源：<mark-list|exported-grade-table|both>
预期写入：<expected_written>
已验证写入：<verified_written>
分数不一致：<mismatches 或 none>
状态异常：<status_regressions 或 none>

结论：<全部一致|存在不一致，暂不继续修复>
```

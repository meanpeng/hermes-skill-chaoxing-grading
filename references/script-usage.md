# Script Usage

This file is a command cookbook. It does not define permission to proceed. Read `agent-rules.md` and confirm the required gates before using these commands.

## Install Dependencies

```bash
python -m pip install -r requirements.txt
```

## Login Cookie

Use this only when login is needed. Do not print passwords in logs.

```bash
python scripts/chaoxing_login_cookie.py --phone "188xxxx1234" --cookie-file ./cx_cookies.txt
```

Before logging in again, use the skill directory as the working directory and keep the cookie file at the relative path `./cx_cookies.txt`. This path works from Bash, zsh, and Windows PowerShell when commands are run from the skill directory. If a previous run saved cookies elsewhere, copy or move that file back to `./cx_cookies.txt` instead of continuing with an environment-specific absolute path.

Check the skill-local cookie file before logging in again:

```bash
python scripts/check_cookie.py --cookie-file ./cx_cookies.txt
```

For JSON:

```bash
python scripts/check_cookie.py --cookie-file ./cx_cookies.txt --json
```

Legacy curl fallback for Bash/zsh or real `curl.exe` on Windows:

```bash
curl -s -b ./cx_cookies.txt "https://i.chaoxing.com" -o /dev/null -w "%{http_code}"
```

Treat `200` as likely valid and `302` as expired.

Browser state is not the same as script/API state. If a browser tab redirects to the Chaoxing login page but `check_cookie.py` reports the cookie file is valid, continue script/API operations with the validated `--cookie-file` path and mention the mismatch in the run report.

## Read-Only Course/Class/Assignment/Exam Discovery

Use this after login to avoid model-specific browser exploration for the orientation phase:

```bash
python scripts/chaoxing_discover.py \
  --cookie-file ./cx_cookies.txt \
  --course "人工智能原理" \
  --class-contains "闵"
```

Use JSON for downstream tooling:

```bash
python scripts/chaoxing_discover.py \
  --cookie-file ./cx_cookies.txt \
  --course "人工智能原理" \
  --class-contains "闵" \
  --json
```

If the account has multiple teacher courses and the target course is not known, scan matching classes across all courses:

```bash
python scripts/chaoxing_discover.py \
  --cookie-file ./cx_cookies.txt \
  --class-contains "闵"
```

Without `--course` or `--class-contains`, the script lists available courses with `courseid` and `cpi` instead of failing.

If course selection is already known, skip course-list matching:

```bash
python scripts/chaoxing_discover.py \
  --cookie-file ./cx_cookies.txt \
  --courseid 204565237 \
  --cpi 492206399 \
  --class-contains "闵"
```

This script is read-only orientation. It reports assignments, exams, counts, and same-name assignment/exam conflicts; it does not open student submissions, export files, draft grades, or submit anything.

When a requested task name appears in both `assignments` and `exams`, ask the teacher to choose the task type before continuing.

## Extract Downloaded Assignment Zip

Use only after the teacher has confirmed `concise` or `detailed` scoring. Skip entirely for `random` scoring.

## Package And Download Assignment Zips

Use only after the teacher has confirmed `concise` or `detailed` scoring and the dry-run target list is correct. The script is dry-run by default:

```bash
python scripts/download_work_zips.py \
  --cookie-file ./cx_cookies.txt \
  --course "人工智能原理" \
  --class-contains "闵" \
  --assignment-contains "实验五" \
  --format word
```

Confirmed download:

```bash
python scripts/download_work_zips.py \
  --cookie-file ./cx_cookies.txt \
  --course "人工智能原理" \
  --class-contains "闵" \
  --assignment-contains "实验五" \
  --format word \
  --output-dir downloads/ai-principles \
  --confirm-download
```

Formats: `word`, `pdf`, or `attachment`. Use repeated `--work-id` options to download exact assignments instead of matching by title.

## Prepare Downloaded Materials

For downloaded zip files, use the batch preparation script instead of manually extracting each package:

```bash
python scripts/prepare_work_materials.py \
  --zip-dir downloads/ai-principles \
  --output-dir prepared/ai-principles \
  --mode metrics \
  --sample 5
```

For one zip:

```bash
python scripts/prepare_work_materials.py \
  --zip-file output.zip \
  --output-dir prepared/output \
  --mode metrics
```

This writes per-assignment `grading_materials.csv` or `grading_metrics.csv` files, an `agent_material_report.md`, and `materials_manifest.csv/json`.

This script must not generate draft scores. It only prepares extraction/statistics evidence for later agent or teacher judgment.

```bash
python scripts/extract_work_zip.py output.zip -d output_dir
```

## Prepare Exported Exam Word Records

Use only for confirmed exam `detailed` mode. Exams do not use `random` or `concise` scoring. Download the complete Word answer record package from the exam mark list; do not rely on the attachment-only package for full-class grading.

```bash
python scripts/prepare_exam_materials.py \
  --input-dir downloads/exam-word-extract \
  --output-dir prepared-exam/exam-title \
  --json
```

This writes `exam_materials.csv/json`, per-student Markdown reports, and embedded answer images. It prepares evidence only; it does not draft or submit scores.

## Prepare Material Metadata

Use only for `concise` or `detailed` mode.

```bash
python scripts/batch_grade.py --base-dir output_dir --mode materials
python scripts/batch_grade.py --base-dir output_dir --mode metrics
python scripts/batch_grade.py --base-dir output_dir --mode metrics --sample 5
```

Metrics are evidence aids, not final grades.

## Dry-Run Score Submission

Use this before any write. Dry-run validates the CSV and prints the pending list.

```bash
python scripts/batch_submit_scores.py \
  --courseid COURSEID \
  --clazzid CLAZZID \
  --work-id WORK_ID \
  --scores-csv scores.csv
```

For exams, validate a reviewed total-score CSV against the exam mark list:

```bash
python scripts/submit_exam_scores.py \
  --cookie-file ./cx_cookies.txt \
  --courseid COURSEID \
  --clazzid CLAZZID \
  --cpi CPI \
  --relationid EXAM_RELATION_ID \
  --scores-csv reviewed_exam_scores.csv
```

## Confirmed Submit Mode

Use only after the teacher has explicitly confirmed the exact final score list and write plan in the current turn.

Preferred list-page API path:

```bash
python scripts/submit_scores.py \
  --cookie-file ./cx_cookies.txt \
  --courseid COURSEID \
  --clazzid CLAZZID \
  --cpi CPI \
  --work-id WORK_ID \
  --scores-csv final_scores.csv \
  --method list-input
```

Confirmed write:

```bash
python scripts/submit_scores.py \
  --cookie-file ./cx_cookies.txt \
  --courseid COURSEID \
  --clazzid CLAZZID \
  --cpi CPI \
  --work-id WORK_ID \
  --scores-csv final_scores.csv \
  --method list-input \
  --confirm-submit
```

Confirmed exam write, only after the teacher confirms the exact reviewed score list:

```bash
python scripts/submit_exam_scores.py \
  --cookie-file ./cx_cookies.txt \
  --courseid COURSEID \
  --clazzid CLAZZID \
  --cpi CPI \
  --relationid EXAM_RELATION_ID \
  --scores-csv reviewed_exam_scores.csv \
  --confirm-submit
```

## Post-Submit Exported Grade Verification

After a confirmed write, verify with the list page first, then use the exported grade table as the independent source of truth:

```bash
python scripts/verify_score_export.py \
  --cookie-file ./cx_cookies.txt \
  --courseid COURSEID \
  --clazzid CLAZZID \
  --cpi CPI \
  --work-id WORK_ID \
  --scores-csv final_scores.csv
```

By default the script keeps the downloaded workbook in memory only. Add `--output-file verification.xls` only when the teacher explicitly wants to retain the exported grade table.

Fallback individual review-page helper:

```bash
python scripts/batch_submit_scores.py \
  --courseid COURSEID \
  --clazzid CLAZZID \
  --work-id WORK_ID \
  --scores-csv scores.csv \
  --confirm-submit
```

This requires a browser automation Python environment that provides `cdp(...)` and `js(...)`.

## XLS Export/Edit/Import

Use only when all students are submitted, or unsubmitted rows have been removed and the teacher has confirmed the exact import plan.

Required preflight:

```text
all_students_submitted: yes/no
unsubmitted_rows_removed: yes/no/not-applicable
export_enc_collected: yes/no
import_enc_collected: yes/no
modified_file_saved_as_xlsx_then_copied_to_xls: yes/no
teacher_confirmed_exact_score_list: yes/no
```

If any answer is `no`, do not import.

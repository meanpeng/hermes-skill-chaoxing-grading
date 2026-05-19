# chaoxing-assignment-grading

Chaoxing/Xuexitong teacher-side assignment grading helper for AI agents and manual workflows.

The project focuses on the safe parts of the grading workflow:

- log in and save Chaoxing cookies
- navigate courses, classes, assignments, and review pages
- extract exported assignment packages
- organize `.docx` / `.doc` reports for agent reading
- preview batch score submissions in dry-run mode
- submit scores only after explicit teacher confirmation
- verify submitted scores from Chaoxing's exported grade table

## Safety Rule

Never submit grades automatically. The final action that writes scores to Chaoxing must be confirmed by the teacher after they see the exact score list.

`scripts/batch_submit_scores.py` defaults to dry-run. It prints the pending list and does not navigate, fill scores, or submit unless `--confirm-submit` is passed in a browser automation environment.

## Install

```bash
git clone https://github.com/meanpeng/hermes-skill-chaoxing-grading.git
cd hermes-skill-chaoxing-grading
python -m pip install -r requirements.txt
```

Use a UTF-8 capable terminal for Chinese output. On Windows PowerShell, Python script output is normally fine; if `Get-Content` shows garbled Chinese, set the terminal encoding to UTF-8 before reading Markdown files.

## Login

```bash
python scripts/chaoxing_login_cookie.py --phone "188xxxx1234" --cookie-file cx_cookies.txt
```

Omit `--password` so the password is typed without echo. The cookie file is local working data and should not be committed.

Check whether a saved cookie is still usable:

```bash
python scripts/check_cookie.py --cookie-file cx_cookies.txt
```

## Read-Only Discovery

For the orientation phase, prefer the discovery script over manual browser exploration:

```bash
python scripts/chaoxing_discover.py \
  --cookie-file cx_cookies.txt \
  --course "人工智能原理" \
  --class-contains "闵"
```

It outputs course ids, matching class ids, assignment `workId` values, submitted counts, pending-review counts, and unsubmitted counts. It is read-only and does not open student submissions or write grades.

If the account has multiple teacher courses and the target course is not known, omit `--course` and keep the class hint:

```bash
python scripts/chaoxing_discover.py \
  --cookie-file cx_cookies.txt \
  --class-contains "闵"
```

The script scans all teacher courses and returns only courses with matching classes. If neither `--course` nor `--class-contains` is provided, it lists available courses with `courseid` and `cpi`.

## Manual Browser Flow

1. Log in to `https://passport2.chaoxing.com/login`.
2. Open the course list from the personal space.
3. Enter the target course.
4. Open the assignment list.
5. Confirm the current class and assignment before exporting or reviewing.
6. Open the review list and record:
   - course name and `courseid`
   - current class name and `clazzid`
   - assignment name and `workId`
   - submitted / pending counts
7. Open individual review pages to read answers or attachments.
8. Stop before clicking `提交`, `提交并进入下一份`, or `打回`.

Class context matters. Chaoxing may show "all classes" on the assignment list but switch to one selected class on the review list. Always re-check the visible class name and counts after entering the review list.

## Extract Exported Assignment Packages

After the teacher confirms `concise` or `detailed` scoring, use the dry-run-first downloader to package and download assignment zips:

```bash
python scripts/download_work_zips.py \
  --cookie-file cx_cookies.txt \
  --course "人工智能原理" \
  --class-contains "闵" \
  --assignment-contains "实验五" \
  --format word
```

Add `--confirm-download` only after the target list is correct:

```bash
python scripts/download_work_zips.py \
  --cookie-file cx_cookies.txt \
  --course "人工智能原理" \
  --class-contains "闵" \
  --assignment-contains "实验五" \
  --format word \
  --output-dir downloads/ai-principles \
  --confirm-download
```

Supported package formats are `word`, `pdf`, and `attachment`.

Prepare downloaded zips into per-assignment CSVs:

```bash
python scripts/prepare_work_materials.py \
  --zip-dir downloads/ai-principles \
  --output-dir prepared/ai-principles \
  --mode metrics \
  --sample 5
```

The preparation script writes one `grading_metrics.csv` or `grading_materials.csv` per zip, one `agent_material_report.md` per zip, plus `materials_manifest.csv/json`. It does not create draft scores.

```bash
python scripts/extract_work_zip.py output.zip -d output_dir
```

The extractor handles common UTF-8 and GBK filename encodings and rejects unsafe zip paths.

## Organize Materials

Default mode only prepares material metadata for reading:

```bash
python scripts/batch_grade.py --base-dir output_dir
```

Metric-assisted mode adds rough section and reflection signals, but it still does not grade:

```bash
python scripts/batch_grade.py --base-dir output_dir --mode metrics
```

Useful options:

```bash
python scripts/batch_grade.py --base-dir output_dir --sample 5
python scripts/batch_grade.py --base-dir output_dir --min-chars 30
```

CSV output includes:

- `status`: `ok`, `too_short`, `missing_report`, or `unreadable`
- `format`: `docx`, `doc`, or `none`
- `char_count`
- `img_count`
- `expanded_zip`
- `report_path`
- `preview`

`too_short` means a report was found and parsed, but the extracted text is below the configured threshold. It is different from `missing_report`.

## Dry-Run Batch Submission

Create a CSV such as:

```csv
student_id,score,workAnswerId
255080235,92,55259467
255080225,88,55265135
```

Preview the pending list:

Preferred list-page API path:

```bash
python scripts/submit_scores.py \
  --cookie-file cx_cookies.txt \
  --courseid 204565237 \
  --clazzid 139247126 \
  --cpi 492206399 \
  --work-id 53469238 \
  --scores-csv scores.csv \
  --method list-input
```

Only after teacher confirmation, add `--confirm-submit`. The script writes through Chaoxing's `/work/markscore` endpoint one `workAnswerId` at a time.

After a confirmed write, verify against the exported grade table:

```bash
python scripts/verify_score_export.py \
  --cookie-file cx_cookies.txt \
  --courseid 204565237 \
  --clazzid 139247126 \
  --cpi 492206399 \
  --work-id 53469238 \
  --scores-csv scores.csv
```

The verifier downloads the grade export, parses it in memory, and compares the submitted targets against the exported score/status rows. Use `--output-file` only when the teacher explicitly wants to keep the downloaded table.

Fallback individual review-page path:

```bash
python scripts/batch_submit_scores.py \
  --courseid 204565237 \
  --clazzid 142468056 \
  --work-id 53109750 \
  --scores-csv scores.csv
```

Dry-run output validates the scores and prints the first review URL. It does not write anything.

Only after the teacher explicitly confirms the final list, rerun in a browser automation environment with:

```bash
python scripts/batch_submit_scores.py \
  --courseid 204565237 \
  --clazzid 142468056 \
  --work-id 53109750 \
  --scores-csv scores.csv \
  --confirm-submit
```

## Script Reference

- `scripts/chaoxing_login_cookie.py`: login through Chaoxing API and save cookies in MozillaCookieJar format
- `scripts/check_cookie.py`: verify whether saved cookies still reach Chaoxing personal space
- `scripts/chaoxing_discover.py`: read-only discovery of teacher courses, classes, assignments, and counts
- `scripts/download_work_zips.py`: dry-run-first batch package/download helper for assignment zip files
- `scripts/prepare_work_materials.py`: batch extract downloaded zips and prepare material/metric CSVs
- `scripts/extract_work_zip.py`: cross-platform safe zip extraction
- `scripts/batch_grade.py`: prepare report metadata and CSV material lists
- `scripts/submit_scores.py`: dry-run-first list-page API score submission helper
- `scripts/verify_score_export.py`: post-submit verification from Chaoxing's exported grade table
- `scripts/batch_submit_scores.py`: dry-run-first score submission helper

## Notes for Agents

- Before downloading or inspecting assignments, ask the teacher to confirm the score range and scoring mode: random, concise, or detailed.
- Prefer reading a few representative submissions first and calibrating the rubric with the teacher.
- Use text length and image count as navigation signals, not as grades.
- For `.docx`, read both paragraphs and table cells.
- For `.doc`, text extraction is best-effort and image count is estimated from file size.
- Never commit cookies, downloaded student submissions, or generated grading reports unless the teacher explicitly asks.

For more consistent behavior across different models, use:

- `references/agent-rules.md`: short mandatory rule contract for every model
- `references/workflow-checklist.md`: explicit context ledger, calibration gate, write preflight, and verification checklist
- `references/scoring-methodology.md`: first-pass scoring bands and mandatory human/model review overrides
- `references/script-usage.md`: script command cookbook separated from workflow authority
- `references/browser-harness-fallback.md`: script-failure fallback map for Browser harness discovery, download, submit, and verification
- `references/playwright-submit-fallback.md`: fallback submit flow when browser-harness helpers are unavailable
- `references/steps/`: phase-specific details; read only the file for the current workflow step
- `references/full-workflow-legacy.md`: archived long workflow retained for older page/API details

## License

MIT

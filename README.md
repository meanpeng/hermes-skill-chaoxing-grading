# chaoxing-assignment-grading

Chaoxing/Xuexitong teacher-side assignment grading helper for AI agents and manual workflows.

The project focuses on the safe parts of the grading workflow:

- log in and save Chaoxing cookies
- navigate courses, classes, assignments, and review pages
- extract exported assignment packages
- organize `.docx` / `.doc` reports for agent reading
- preview batch score submissions in dry-run mode
- submit scores only after explicit teacher confirmation

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
- `scripts/extract_work_zip.py`: cross-platform safe zip extraction
- `scripts/batch_grade.py`: prepare report metadata and CSV material lists
- `scripts/batch_submit_scores.py`: dry-run-first score submission helper

## Notes for Agents

- Prefer reading a few representative submissions first and calibrating the rubric with the teacher.
- Use text length and image count as navigation signals, not as grades.
- For `.docx`, read both paragraphs and table cells.
- For `.doc`, text extraction is best-effort and image count is estimated from file size.
- Never commit cookies, downloaded student submissions, or generated grading reports unless the teacher explicitly asks.

## License

MIT

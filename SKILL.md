---
name: chaoxing-assignment-grading
description: "Use when grading Chaoxing/Xuexitong assignments. Teacher workflow: login, browse courses/classes/assignments, inspect submissions, organize exported materials, draft scores, and submit only after explicit confirmation."
version: 1.1.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [chaoxing, xuexitong, grading, education, assignment, automation]
    related_skills: [browser-harness]
---

# Chaoxing Assignment Grading

Use this skill for teacher-side Chaoxing/Xuexitong assignment grading workflows.

## Non-Negotiable Safety Rule

You may inspect pages, open previews, download/export attachments, parse documents, and draft score suggestions.

Before changing grades, comments, plagiarism markers, return status, or clicking `提交`, `提交并进入下一份`, `完成`, or `打回重做`, show the exact planned action and wait for explicit teacher confirmation.

## Workflow

### 1. Login

If the user already provided the account for this turn, use it. Do not repeat the password in logs or reports.

```bash
python scripts/chaoxing_login_cookie.py --phone "188xxxx1234" --cookie-file cx_cookies.txt
```

Omit `--password` when possible so the password is entered without echo.

### 2. Course Selection

Open the course list and identify available teacher courses. If the target course was not specified, present the course names and ask the teacher to choose.

Common entry points:

- personal space: `https://i.chaoxing.com`
- course list iframe: `/visit/interaction?...`
- teacher course page: `/mooc2-ans/mycourse/tch?courseid=...&clazzid=...&cpi=...`

### 3. Assignment And Class Context

Open the assignment list:

```text
https://mooc2-ans.chaoxing.com/mooc2-ans/work/list?courseid=COURSEID&clazzid=CLAZZID&cpi=CPI
```

Before exporting or grading, record and show:

- course name and `courseid`
- visible class name and `clazzid`
- assignment title and `workId`
- submitted / pending / missing counts

Important: Chaoxing may show an all-class assignment card, then switch to a specific class on the review list. Re-check the visible class name and counts after entering the review list.

### 4. Review List

Open the assignment's `批阅` link. Student rows usually expose `workAnswerId` through:

```js
Array.from(document.querySelectorAll('a[onclick*="toMarkWork"]')).map(a => ({
  data: a.getAttribute('data'),
  rowText: (a.closest('li') || a.closest('tr') || a.parentElement).innerText
}))
```

Use this mapping when preparing a score CSV:

```csv
student_id,score,workAnswerId
255080235,92,55259467
```

### 5. Inspect Submissions

Open one student's review page before batch work. Read:

- answer text
- attachments and previews
- student name / id / class
- score boxes and comment boxes

Do not fill scores or comments unless the teacher has confirmed that exact change.

### 6. Export And Organize Attachments

If the teacher wants batch grading from exported files:

```bash
python scripts/extract_work_zip.py output.zip -d output_dir
python scripts/batch_grade.py --base-dir output_dir
```

For calibration:

```bash
python scripts/batch_grade.py --base-dir output_dir --sample 5
```

For optional rough signals:

```bash
python scripts/batch_grade.py --base-dir output_dir --mode metrics
```

Treat these fields as reading aids, not automatic grades:

- `status`: `ok`, `too_short`, `missing_report`, `unreadable`
- `char_count`
- `img_count`
- `section_signal`
- `reflection_signal`

### 7. Draft Scores

Start with 3-5 representative submissions and calibrate the rubric with the teacher. After the teacher accepts the rubric, continue with the rest.

Conservative report-grading posture:

- 90-100: complete report, correct task match, clear process/results, screenshots or evidence, source/code when required
- 80-89: mostly complete, minor omissions in analysis, screenshots, or conclusions
- 70-79: task covered but important evidence, code, or explanation is missing
- 60-69: minimal completion with weak report or incomplete evidence
- below 60: major missing artifacts, irrelevant submission, empty content, or confirmed serious issue

### 8. Dry-Run Submission

Preview first:

```bash
python scripts/batch_submit_scores.py \
  --courseid COURSEID \
  --clazzid CLAZZID \
  --work-id WORK_ID \
  --scores-csv scores.csv
```

Show the dry-run list to the teacher. Only after explicit confirmation, run the submit mode in a browser automation environment:

```bash
python scripts/batch_submit_scores.py \
  --courseid COURSEID \
  --clazzid CLAZZID \
  --work-id WORK_ID \
  --scores-csv scores.csv \
  --confirm-submit
```

## Pitfalls

- Current class context is easy to lose. Always confirm class name and counts on the review list.
- `vc3` and `p_auth_token` are httpOnly cookies; use the cookie file or CDP-style injection, not `document.cookie`.
- For `.docx`, read paragraphs and table cells.
- For `.doc`, text extraction is best-effort and image count is an estimate.
- Short parsed reports are `too_short`, not `missing_report`.
- Do not commit cookies, downloaded submissions, generated reports, or score CSVs containing student data unless explicitly requested.

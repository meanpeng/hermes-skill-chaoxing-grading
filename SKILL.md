---
name: chaoxing-assignment-grading
description: "Use when grading Chaoxing/Xuexitong assignments or exams. Teacher workflow: identify course/class/task, confirm scoring setup, optionally inspect/export materials, draft scores, and submit only after explicit confirmation."
version: 2.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [chaoxing, xuexitong, grading, education, assignment, automation]
    related_skills: [browser-harness]
---

# Chaoxing Assignment And Exam Grading

Use this skill for teacher-side Chaoxing/Xuexitong assignment and exam grading workflows.

## Mandatory Rule Loading

For every run, read `references/agent-rules.md` first. It is the short rule contract and overrides every script example, browser snippet, API snippet, and step guide.

Use `references/workflow-checklist.md` as the live checklist. Use step files only when the current phase needs implementation details.

Scripts are tools, not workflow authority. A command example never grants permission to open submissions, export, download, inspect, import, submit, return work, or otherwise write unless the rules and current teacher confirmation allow that step.

## Script-First Discovery

For read-only orientation, use the stable scripts before agent/browser exploration:

1. Check saved cookies with `scripts/check_cookie.py`.
2. If needed, log in with `scripts/chaoxing_login_cookie.py`.
3. Discover teacher courses, matching classes, assignments, exams, and counts with `scripts/chaoxing_discover.py`.
4. Use browser DOM exploration only when the discovery script fails or the page structure has changed. If a fallback is needed, report the failure and the fallback evidence.

The discovery script is allowed only for Step 1 orientation. It must not open individual student submissions, export/download materials, draft scores, or write grades.

## Cookie And Session Reality Check

Treat the browser session and the script/API cookie session as separate state. A Chaoxing page opened in the browser may redirect to the login page while the local MozillaCookieJar file still works for scripts and API calls. Do not conclude that the script session is expired from the browser redirect alone; verify with `scripts/check_cookie.py` against the cookie file and report both facts when they disagree.

Use the skill directory as the default working directory and keep the cookie file at the relative path `./cx_cookies.txt`. This relative path is the cross-platform contract for Linux, macOS, and Windows. Run scripts from the skill directory or pass `--cookie-file ./cx_cookies.txt` explicitly. If a previous run saved cookies elsewhere, use the platform's normal file search only to migrate or copy it back into the skill directory; do not make environment-specific absolute paths part of the normal workflow.

## Non-Negotiable Safety Rule

You may inspect pages, open previews, download/export attachments, parse documents, and draft score suggestions only within the confirmed scoring mode.

Before changing grades, comments, plagiarism markers, return status, or clicking `提交`, `提交并进入下一份`, `完成`, or `打回重做`, show the exact planned action and wait for explicit teacher confirmation in the current turn.

Exam-specific constraint: exams do not support `random` or `concise` scoring in this skill. For exams, use `detailed` only, export the complete Word answer record, inspect every submitted student's subjective answers, and submit only a reviewed total score plan.

## State Machine

Keep every run in this explicit order:

1. **Orient**: identify the course, class, task type, assignment/exam title, submitted count, unsubmitted count, and current page URL. When listing a class, show assignments and exams together. If a provided task name matches both an assignment and an exam, ask the teacher which type to use.
2. **Confirm scoring setup**: before opening submissions, exporting, packaging, downloading, extracting, or parsing files, ask the teacher to confirm score range and scoring mode.
3. **Prepare evidence according to mode**:
   - `random`: do not open, export, download, extract, parse, or inspect assignment files.
   - `concise`: use exported metadata and metrics as rough evidence; inspect flagged cases only.
   - `detailed`: inspect every available assignment file before scoring.
4. **Draft scores**: produce the fixed score draft schema with evidence.
5. **Preflight write**: show exact target, score list, write method, unsubmitted count, and manual-review count.
6. **Confirm write**: write only after explicit current-turn teacher confirmation of that exact final plan.
7. **Verify**: re-open the list and download the exported grade table, compare the exact submitted scores, and report mismatches.

Required ledger:

```text
course: <name> | courseid=<id>
class: <name> | clazzid=<id>
task: assignment <title> | workId=<id>
task: exam <title> | relationid=<id> | paperId=<id>
counts: submitted=<n> pending_review=<n> unsubmitted=<n>
score_range: <min>-<max> | confirmed=<yes/no>
scoring_mode: random | concise | detailed | confirmed=<yes/no>
method: read-only | list-input | export-edit-import | individual-submit
verification: mark-list | exported-grade-table | both
write_allowed: no until explicit teacher confirmation
```

## Step Guides

Read only the guide for the current phase:

- `references/steps/01-login.md`: login, cookie checks, and cookie injection.
- `references/steps/02-course-assignment.md`: course, class, assignment/exam, and review-list discovery.
- `references/steps/03-scoring-setup.md`: score range and scoring mode confirmation.
- `references/steps/04-materials.md`: export, download, extract, and material metadata preparation.
- `references/steps/05-draft-scores.md`: random, concise, and detailed score drafting.
- `references/steps/06-submit-verify.md`: dry-run, preflight, confirmed submission/import, and verification.

Supporting references:

- `references/agent-rules.md`: mandatory short rules.
- `references/workflow-checklist.md`: run checklist.
- `references/scoring-methodology.md`: scoring bands, concise-mode methodology, score jitter, CRC-32 docx workaround, pending-student discovery, essay scoring tier system.
- `references/wordml-doc-extraction.md`: extracting text from WordML flat XML `.doc` files (学生答案 section), binary .doc via antiword, case-insensitive .DOCX matching, orphan file fallback.
- `references/essay-grading.md`: text-based essay assignment grading (一课一文, 调研报告) — word count, personal thinking, dimension coverage.
- `references/competition-ranking-scoring.md`: grading assignments by MNIST competition ranking (实验五 workflow, score bands, edge cases).
- `references/script-usage.md`: script command cookbook.
- `references/browser-harness-fallback.md`: Browser harness fallback map when a script fails or page/API structure changes.
- `references/chaoxing-anti-bot-login.md`: Chaoxing anti-bot bypass worked example — AES login API, CDP cookie injection, iframe navigation patterns, and homework/work API endpoints.
- `references/playwright-submit-fallback.md`: fallback submission approach.
- `references/full-workflow-legacy.md`: archived long workflow with older page/API details.
- `references/exam-objective-scores.md`: extracting auto-graded objective scores from markpaper (exams only).
- `references/mnist-competition-grading.md`: grading experiment 5 based on MNIST classroom competition rankings instead of report content.

## Exam Notes

The exam page is reachable from the course navigation item under the assignment button (`/mooc2-ans/exam/test`). In the mark list, use the complete Word answer record export rather than attachment-only export. Attachment-only zips include only students who uploaded files and are not sufficient for grading all submitted exams.

For the Word answer record package, use:

- `scripts/download_exam_zips.py`: dry-run-first package/downloader for exam Word answer records or attachment packages. Prefer this script before browser fallback.
- `scripts/prepare_exam_materials.py`: parse flat Chaoxing exam Word/HTML `.doc` exports, extract subjective answers and embedded answer images, and write per-student Markdown plus CSV/JSON.
- `scripts/submit_exam_scores.py`: dry-run-first total score writer for exam mark lists, using `/mooc2-ans/exam/test/batch-markscore` with `way=singlesum`.

Exam score drafts should preserve the objective score exported by Chaoxing and add reviewed subjective scores. Do not generate random or rough exam scores.

**Critical**: The Word export does NOT contain objective scores. Extract them from the markpaper page using `references/exam-objective-scores.md` before drafting totals.

## Output Contracts

Teacher-facing score drafts and write confirmations must use concise Chinese Markdown tables, not raw CSV. Keep raw metrics and CSV rows for machine scripts, saved artifacts, or teacher-requested audit details.

Calibration table for `concise` or `detailed` modes:

```text
student_id | student_name | chars | images | sections | key_requirement | status | provisional_band | notes
```

Score draft schema:

```csv
student_id,student_name,score,band,evidence,penalty_reason,needs_manual_review,workAnswerId
```

Every score must be inside the teacher-confirmed score range. In `random` mode, evidence must state `teacher-selected random scoring; assignment not inspected`.

## Pitfalls

- Browser login state and script cookie state can disagree; a browser redirect to login does not invalidate a separately stored cookie file by itself.
- Keep `cx_cookies.txt` in the skill directory as `./cx_cookies.txt`; avoid baking environment-specific absolute paths into commands or paths into the normal workflow.
- **Word导出不含客观题分数**：`download_exam_zips.py --format word` 导出的所有学生的 `exported_score` 都是 0。客观题实际分数存储在超星的 markpaper 页面中，需要通过浏览器访问 `markUrl` 提取 `fullScore<id>` 和 `score<id>` 输入框的值。
- **markpaper页面是JS渲染的**：markpaper 页面通过 JavaScript 动态加载题目和分数数据，curl 只能获取空壳 HTML。必须用浏览器（如 Obscura）加载页面并等待渲染完成后提取数据。浏览器需要先登录超星。
- **脚本优先原则**：用户明确要求"不要用浏览器，用脚本"。如果脚本能完成的任务，不要切换到浏览器。只有在脚本无法获取数据（如 JS 渲染页面）时才使用浏览器作为 fallback。
- Do not download or inspect assignment files before score range and mode are confirmed.
- Do not use XLS import when unsubmitted rows are present unless they are removed and the exact import plan is confirmed.
- Do not treat `batch_grade.py` metrics as final grades by themselves.
- Do not claim content quality in `random` mode.
- Do not submit scores until the teacher has seen the exact score list and explicitly confirmed it.
- Do not commit cookies, downloaded student submissions, generated score CSVs containing student data unless explicitly requested.
- **CRC-32 corrupted DOCX**: When `python-docx` fails with `Bad CRC-32 for file 'word/media/imageN.png'`, the text is still recoverable by extracting `word/document.xml` from the zip directly. See `references/scoring-methodology.md` → "Handling CRC-32 Corrupted DOCX Files". This counts as agent-side direct inspection; score the student using recovered char/img counts.
- **Uniform scores in concise mode**: The first-pass formula often gives everyone the same score. Teachers reject uniform scores. Always apply ±1-2 random jitter (with a fixed seed for reproducibility) clamped to the teacher-confirmed floor before showing the draft. See `references/scoring-methodology.md` → "Score Differentiation".
- **Partially-graded assignments**: When only some students need grading (pending_review < submitted), use a dry-run with a dummy all-students CSV to find `current=0` rows, then submit only for those students. See `references/scoring-methodology.md` → "Finding Pending Students".
- **Class name search**: Students/teachers may use abbreviated class names (e.g., "智科2301" vs the actual "智能科技2301-闵"). Always search with `--class-contains "闵"` (the teacher's name suffix) to find the right class when the abbreviated name doesn't match.
- **Script failure → check GitHub first**: When a script (especially `download_exam_zips.py`, `submit_exam_scores.py`, or any recently-added script) fails with unexpected errors (missing arguments, unrecognized flags, API changes), check if the skill repo on GitHub has a newer version before falling back to browser automation. The user's source repo is `meanpeng/hermes-skill-chaoxing-grading`. Update by cloning to `/tmp/` and rsync-ing to the skill directory (preserve `cx_cookies.txt` and local `exam_materials/`).
- **Exam Word export ≠ scores**: The Word answer record export (`download_exam_zips.py --format word`) does NOT include objective scores — `exported_score` will be `0` for all students. The actual auto-graded objective scores live in the markpaper page. See `references/exam-objective-scores.md` for extraction workflow.
- **Exam markpaper score structure**: On the markpaper page, `fullScore<id>` hidden inputs hold the per-question maximum, and `score<id>` text inputs hold the student's actual score (readonly). Both must be read; comparing them reveals which questions the student got wrong. The `sumScore` input shows the total but starts at 0 until the teacher submits.
- **Students in mark-list but not in downloaded materials**: A student may appear in the Chaoxing mark-list (with a `current=0` score) but NOT in the downloaded assignment zip's `grading_metrics.csv`. This happens when the student registered under a different name, joined the class late, or their submission used a non-standard file name. To find their student ID, query the mark-list API directly (fetch pages 1 and 2, parse HTML for name→student_id). See `references/competition-ranking-scoring.md` step 2 for code.
- **Competition-ranking-based scoring**: When grading 实验五 (or similar competition-tied assignments), the teacher may ask to score by MNIST competition ranking instead of report content. Use `session_search` to find past scoring schemes if the teacher references a previous class. See `references/competition-ranking-scoring.md` for the full workflow, score bands, and edge case handling.
- **Partial batch grading**: When `pending_review < submitted` (only some students need grading), run a dry-run with a dummy all-students CSV to find rows with `current=0`, then submit a CSV containing only those pending students. This avoids overwriting existing grades.
- **CRC-32 corrupted docx**: When `python-docx` throws `Bad CRC-32`, the file is still readable. Open it as a zip and extract text from `word/document.xml` directly. See `references/scoring-methodology.md` → "Handling CRC-32 Corrupted DOCX Files".
- **Concise mode uniformity**: The first-pass formula clusters most students at the same score (e.g., all 95). Always apply ±1-2 jitter with a teacher-confirmed floor before showing drafts. See `references/scoring-methodology.md` → "Score Differentiation".
- **Dual .docx/.doc files in student submissions**: When extracting student submissions from Chaoxing assignment packages, some students may have BOTH a `.docx` and a `.doc` file in their extracted folder. Always prefer `.docx` over `.doc` when both exist — the `.docx` is the actual student submission with full content, while the `.doc` is often a WordML flat XML wrapper (starts with `<?xml version="1.0"?>` and `<w:wordDocument>`) that python-docx cannot open, yielding only ~130 chars of XML metadata instead of the real essay text. If only a `.doc` file exists and it is WordML format, parse it as XML and extract text from `w:t` elements. See `references/steps/04-materials.md` → "Dual File Extraction".
- **Uppercase .DOCX extension**: Some students upload files with uppercase `.DOCX` extension. File matching that only checks `.lower().endswith('.docx')` or `.endswith('.docx')` (case-sensitive) will miss these. Always use case-insensitive matching when scanning for docx files. This caused 陈方渲 (233080452) to get 0 extracted text and a default 80 score until caught.
- **WordML .doc with `学生答案` section**: `prepare_work_materials.py` may only extract a subset of students (e.g. 23/33 or 30/34). The missing students have WordML flat XML `.doc` files where the essay text is inside a `<w:t>` element after `学生答案：` and before `正确答案：`, with `<w:br />` tags as line breaks inside the `<w:t>`. Standard WordML parsing (extracting all `w:t` elements) returns ~190 chars because the essay is one giant `w:t` with embedded `<w:br/>` that gets lost. See `references/wordml-doc-extraction.md` for the correct extraction recipe.
- **workAnswerId is class-specific**: When grading multiple classes in sequence, workAnswerIds from one class's mark-list will NOT match another class. Always fetch workAnswerIds fresh from each class's own mark-list using the correct `clazzid` and `workid`. Reusing workAnswerIds from a previous class causes all submissions to fail with "no submitted mark-list row matched" in dry-run.
- **Batch grading multiple classes**: When the teacher says "批X班" after a previous class was just graded with confirmed scoring setup, the scoring parameters (score range, mode, assignment requirements) carry over. Do not re-ask for score range and mode — proceed directly to download, extract, evaluate, and show the draft. Only re-confirm if the assignment title or requirements differ.
- **Essay scoring: dimension coverage is primary factor**: For essay-type assignments (一课一文 etc.) with multi-dimensional requirements (e.g. "技术背景/发展现状/前沿成果/未来方向"), the teacher's explicit preference is that dimension coverage should be the PRIMARY scoring factor — not word count. A student who writes 7000+ words but only covers 4/8 dimension keywords should score LOWER than a student who writes 3000 words but covers 8/8. Word count and personal thinking length are secondary modifiers. Scores must have visible spread (80-100 range, not clustered). 100 is acceptable for truly excellent work. See `references/scoring-methodology.md` → "Essay Scoring Tier System".
- **WordML `.doc` `<w:br/>` truncation**: Chaoxing Word exports embed `<w:br/>` (line break) tags *inside* `<w:t>` elements. Standard regex extraction `re.findall(r'<w:t[^>]*>([^<]+)</w:t>', ...)` truncates at the first `<w:br/>`, silently losing most of the student's answer. Always replace `<w:br/>` with `\n` *before* extracting text, and prefer extracting the "学生答案" → "正确答案" section to isolate the answer from system metadata. See `references/steps/04-materials.md` → "WordML `.doc` Fallback".
- **Case-sensitive `.DOCX` extension**: Chaoxing exports sometimes produce files with uppercase `.DOCX` extension. On Linux, `f.endswith(".docx")` is case-sensitive and will miss these files, causing silent extraction failures. Always use `f.lower().endswith(".docx")` for file matching.
- **batch_submit_scores.py silently no-ops without a browser**: Running `batch_submit_scores.py --confirm-submit` from a plain terminal prints the score list and `CONFIRMED SUBMIT MODE: writing scores to Chaoxing.` but writes NOTHING — its submit path requires a browser automation environment providing `cdp()`/`js()` globals (`require_browser_submit_environment` returns an error only inside `submit_scores()`, after the plan is printed). For terminal/API writes always use `scripts/submit_scores.py --method list-input --confirm-submit`, then re-fetch the mark-list and diff every student's `current` against the CSV (58/58-style verification) before reporting success.
- **Metadata-only evidence is not plagiarism (teacher ruling 2026-09, 实验六)**: Same docx editor account (lastModifiedBy) with NO text/image similarity is not accepted as proof of copying — grade those students normally. Hard evidence requires content overlap: same-bytes real output screenshots, or ≥97% text similarity, or both.
- **Mark-list API pagination**: The mark-list endpoint (`/mooc2-ans/work/mark-list`) requires `pages` and `size` parameters for pagination. Using only `prePageSize`/`prePageNum` (or `pageNum`/`pageSize`) returns the same first 20 students on every page. The server caps page size at 20 regardless of `prePageSize` value. Check `totalPage` in the HTML response to determine how many pages to fetch. See `references/competition-ranking-scoring.md` step 2.
- **指导书抄送检查 (实验八 workflow)**: When the teacher supplies the 实验指导书 and allows copying its 原理/步骤/环境 sections, raw pairwise text similarity is inflated by (a) the guide sections everyone copies and (b) the shared report template (~1000+ chars of 成绩统计表/报告头). Compute per-student `guide_matched` (difflib blocks ≥50 vs normalized guide text, mapped per guide section) plus regex-matched `template_len`, then band pairs on NET similarity = matched − min(ban_a, ban_b). Raw ≥90% pairs can drop to near-zero net (false alarms); genuine copy stays high (e.g. 96.7% net on 8.6k shared analysis prose). Check "0 own images" students separately (`own_img==0`, crest hash excluded) — borrowed same-byte real screenshots violate the teacher's "图和文字得有自己的" rule even when text is independent.
- **pip index broken on this server**: pip.conf points to Tencent internal mirror `mirrors.tencentyun.com` which is unreachable; install with `pip install <pkg> -i https://pypi.org/simple` (e.g. pycryptodome for the login script).


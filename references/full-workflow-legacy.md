---
name: chaoxing-assignment-grading
description: "Use when grading Chaoxing/Xuexitong assignments. Teacher workflow: login, reliably find courses/classes/assignments with Chaoxing page selectors, inspect submissions, organize exported materials, draft scores, and submit only after explicit confirmation."
version: 1.7.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [chaoxing, xuexitong, grading, education, assignment, automation]
    related_skills: [browser-harness]
---

# Chaoxing Assignment Grading

Use this skill for teacher-side Chaoxing/Xuexitong assignment grading workflows.

## Mandatory Loading Order

For every run, keep the active context small and load files in this order:

1. Read `references/agent-rules.md` first. These rules are mandatory and override all cookbook examples.
2. Use `references/workflow-checklist.md` as the live run checklist.
3. Use `references/scoring-methodology.md` only after the teacher confirms the score range and scoring mode.
4. Use `references/script-usage.md` only when a concrete script command is needed.
5. Treat the long workflow below as implementation detail. Do not let script examples override confirmation gates, scoring-mode gates, or write-safety rules.

Scripts are tools, not workflow authority. A command example never grants permission to download, inspect, submit, import, return, or otherwise write unless the rule files allow that step.

## Non-Negotiable Safety Rule

You may inspect pages, open previews, download/export attachments, parse documents, and draft score suggestions.

Before changing grades, comments, plagiarism markers, return status, or clicking `提交`, `提交并进入下一份`, `完成`, or `打回重做`, show the exact planned action and wait for explicit teacher confirmation.

## Model-Stable Execution Protocol

Different models vary most when a task relies on implicit judgment. Keep every run in this explicit state machine:

1. **Orient**: identify the course, class, assignment, submitted count, unsubmitted count, and current page URL. If any field is unknown, collect it before grading.
2. **Confirm scoring setup before downloads**: before exporting, packaging, downloading, or parsing assignment files, ask the teacher to confirm both the score range and scoring mode.
3. **Read-only first**: downloads, exports, document parsing, sampling, and score drafts are allowed only after the scoring setup is confirmed. Page writes and API writes are blocked.
4. **Calibrate when content is used**: for concise or detailed scoring, inspect 3-5 representative submissions before full scoring. Show the calibration table and ask the teacher to accept or adjust the grading posture.
5. **Draft**: produce a full score draft with evidence notes. Treat script metrics as signals only; never convert metrics directly into final grades without reading the actual submission evidence.
6. **Preflight**: before any write, show the exact target class, assignment, students, scores, method, and risk checks.
7. **Confirm**: proceed with writes only after the teacher explicitly confirms the exact plan in the current turn.
8. **Verify**: after writing, re-open or re-export the score/status list and report mismatches.

Required run ledger:

```text
course: <name> | courseid=<id>
class: <name> | clazzid=<id>
assignment: <title> | workId=<id>
counts: submitted=<n> pending_review=<n> unsubmitted=<n>
score_range: <min>-<max> | confirmed=<yes/no>
scoring_mode: random | concise | detailed | confirmed=<yes/no>
method: read-only | list-input | export-edit-import | individual-submit
write_allowed: no until explicit teacher confirmation
```

Default to the safest path unless the teacher explicitly confirms a different allowed mode:

- Use `scripts/batch_grade.py --mode materials` before `--mode metrics`.
- Use list-page direct input over XLS import unless all students are confirmed submitted.
- Use dry-run scripts and CSV validation before any browser/API write.
- Stop at a draft score table if calibration evidence or class context is incomplete.

## Workflow

### 1. Login

If the user already provided the account for this turn, use it. Do not repeat the password in logs or reports.

```bash
python scripts/chaoxing_login_cookie.py --phone "188xxxx1234" --cookie-file cx_cookies.txt
```

Omit `--password` when possible so the password is entered without echo.

The login script performs the old reliable API login path: AES-CBC encryption with key `u2oh6Vu^HWe4_AES`, POST to `/fanyalogin`, and saving cookies with `http.cookiejar.MozillaCookieJar`. Prefer this over `curl -c`, because long `vc3` and `p_auth_token` cookie values can be truncated by some cookie-file flows.

Before logging in again, check whether the existing cookie file still reaches personal space:

```bash
curl -s -b cx_cookies.txt "https://i.chaoxing.com" -o /dev/null -w "%{http_code}"
```

Treat `200` as likely valid and `302` as expired. Do not assume either state without checking when a cookie file exists.

For browser automation, inject saved cookies through CDP rather than `document.cookie`; `vc3` and `p_auth_token` are httpOnly. Enable Network first:

```python
ensure_real_tab()
cdp("Network.enable")
# Load cx_cookies.txt with MozillaCookieJar, then call Network.setCookie for each cookie.
cdp("Page.navigate", url="https://i.chaoxing.com")
```

If a browser helper reports `Unknown Target method: activateTarget`, reuse the current real tab and navigate with `Page.navigate` instead of opening a new tab.

### 2. Course Selection

Open the course list and identify available teacher courses. If the target course was not specified, present the course names and ask the teacher to choose.

Common entry points:

- personal space: `https://i.chaoxing.com`
- course list iframe: `/visit/interaction?...`
- teacher course page: `/mooc2-ans/mycourse/tch?courseid=...&clazzid=...&cpi=...`

Practical course discovery:

```python
# Navigate to the course list iframe when fid is known.
cdp("Page.navigate", url="https://mooc2-ans.chaoxing.com/visit/interaction?fid=YOUR_FID")
```

```js
// Extract visible teacher courses from the current page.
Array.from(document.querySelectorAll("a"))
  .filter(a => a.href.includes("courseId") || a.href.includes("courseid"))
  .map(a => ({
    text: a.innerText.trim(),
    href: a.href,
  }))
  .filter(x => x.text.length > 1);
```

If the user's prompt already names the course, match by partial visible text and open that course directly. If multiple courses match, show the candidate names and ask the teacher to choose.

Key URL patterns:

- course list: `https://mooc2-ans.chaoxing.com/visit/interaction?fid=YOUR_FID`
- teacher course page: `https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/tch?courseid=COURSEID&clazzid=CLAZZID&cpi=CPI`
- assignment list: `https://mooc2-ans.chaoxing.com/mooc2-ans/work/list?courseid=COURSEID&clazzid=CLAZZID&cpi=CPI`

### 3. Assignment And Class Context

Open the assignment list:

```text
https://mooc2-ans.chaoxing.com/mooc2-ans/work/list?courseid=COURSEID&clazzid=CLAZZID&cpi=CPI
```

If class filtering is needed, prefer the direct URL parameter when the class id is known:

```text
https://mooc2-ans.chaoxing.com/mooc2-ans/work/list?courseid=COURSEID&selectClassid=CLAZZID&cpi=CPI&status=-1&v=0&topicid=0
```

Class switcher fallback:

```js
Array.from(document.querySelectorAll("li.classli")).map(el => ({
  text: el.innerText.trim(),
  onclick: el.getAttribute("onclick"),
  data: Array.from(el.attributes).reduce((acc, attr) => {
    acc[attr.name] = attr.value;
    return acc;
  }, {}),
}));
```

To choose a named class:

```js
var items = Array.from(document.querySelectorAll("li.classli"));
var target = items.find(el => el.innerText.trim().includes("TARGET_CLASS_NAME"));
if (target) target.click();
```

Assignment discovery on the work list page should be DOM-driven. The Review links can appear as either `onclick`-triggered links (using `a[onclick*="toMarkWork"]`) or plain `<a>` tags with direct `href` attributes. Try both patterns:

```js
// Try onclick-based links first, fallback to plain href links
var links = Array.from(document.querySelectorAll("a[onclick*='toMarkWork'], a[href*='work/mark']"));
links = links.map(a => {
  var row = a.closest("tr") || a.closest("li") || a.closest(".workList") || a.closest("div") || a.parentElement;
  var data = a.getAttribute("data") || a.href || "";
  var text = row ? row.innerText.trim() : a.innerText.trim();
  var workId = (data.match(/workId=(\d+)/) || data.match(/workid=(\d+)/) || [])[1] || "";
  return { text, data, href: a.href, workId };
}).filter(x => x.text || x.data || x.href);
```

If the prompt already names the assignment, match by row text. If the target is not named, list visible assignment titles/counts and ask the teacher to choose. Do not assume the first row is correct unless the teacher asked for the latest assignment or the page clearly labels it as latest.

Before exporting or grading, record and show:

- course name and `courseid`
- visible class name and `clazzid`
- assignment title and `workId`
- submitted / pending / missing counts

Important: Chaoxing may show an all-class assignment card, then switch to a specific class on the review list. Re-check the visible class name and counts after entering the review list.

### 4. Review List

Open the assignment's `批阅` link. Student rows usually expose `workAnswerId` through:

```js
Array.from(document.querySelectorAll('a[onclick*="toMarkWork"]')).map(a => {
  var row = a.closest("li") || a.closest("tr") || a.closest("div") || a.parentElement;
  var data = a.getAttribute("data") || "";
  var workAnswerId = (data.match(/workAnswerId=(\d+)/) || [])[1] || "";
  return {
    data,
    workAnswerId,
    rowText: row ? row.innerText.trim() : a.innerText.trim(),
  };
});
```

To click the review link for a named assignment from the work list:

```js
var links = Array.from(document.querySelectorAll('a[onclick*="toMarkWork"]'));
var target = links.find(a => {
  var row = a.closest("tr") || a.closest("li") || a.closest("div") || a.parentElement;
  return row && row.innerText.includes("TARGET_ASSIGNMENT_NAME");
});
if (target) target.click();
```

If clicking is unreliable, read the `data` attribute and navigate to its review URL after resolving it against `https://mooc2-ans.chaoxing.com`.

On mark/review pages, global JavaScript variables such as `courseId`, `clazzId`, or `workId` may be unavailable. Prefer hidden inputs for page parameters:

```js
Array.from(document.querySelectorAll("input[type=hidden]")).reduce((result, input) => {
  if (input.name) result[input.name] = input.value;
  return result;
}, {});
```

Use this mapping when preparing a score CSV:

```csv
student_id,score,workAnswerId
255080235,92,55259467
```

### 5. Confirm Score Range And Scoring Mode

Before opening student submissions, exporting, packaging, downloading, or parsing assignment files, ask the teacher to confirm:

1. **Score range**: minimum and maximum score to use, for example `70-100`, `60-95`, or `0-100`.
2. **Scoring mode**:
   - `1. random`: random scoring inside the confirmed score range. Do not download or inspect assignment files. Mark the draft as teacher-directed random scoring with no submission evidence.
   - `2. concise`: rough scoring from metadata such as parsed text length, section signals, reflection signals, image counts, and previews. Download/export is needed, but do not open every file manually unless flagged.
   - `3. detailed`: open and inspect every student's assignment file before assigning scores. Download/export is needed.

Use this prompt shape:

```text
请先确认评分设置：
1. 分数范围：例如 70-100
2. 评分模式：
   1）随机评分：直接在范围内随机打分，不下载/不查看作业
   2）简洁打分：根据字数、结构、图片数量、摘要预览等大致内容打分
   3）细致打分：逐个打开作业文件仔细检查后打分
```

Do not continue to open, export, download, extract, or parse assignment files until both fields are confirmed.

Mode-specific behavior:

- `random`: collect the student list and identifiers from the review/score list page only. Generate random scores within the confirmed range, keep distribution reasonable, and set `evidence` to `teacher-selected random scoring; assignment not inspected`. Do not claim content quality.
- `concise`: run `scripts/batch_grade.py --mode materials` and usually `--mode metrics`; inspect flagged cases only. Evidence may cite status, character count, images, section/reflection signals, and preview.
- `detailed`: open every available report/attachment. Evidence must cite actual observed content, not only metrics.

### 6. Inspect Submissions

Only use this section after the teacher has confirmed `concise` or `detailed` scoring. If the mode is `random`, do not open student submissions.

Open one student's review page before batch work. Read:

- answer text
- attachments and previews
- student name / id / class
- score boxes and comment boxes

Do not fill scores or comments unless the teacher has confirmed that exact change.

### 7. Export And Organize Attachments

Only use this section after the teacher has confirmed `concise` or `detailed` scoring. If the mode is `random`, skip export/download/extraction entirely.

If the teacher wants batch grading from exported files and already has a downloaded zip:

```bash
python scripts/extract_work_zip.py output.zip -d output_dir
python scripts/batch_grade.py --base-dir output_dir
```

If the zip has not been exported yet, use the page context to trigger Chaoxing's package job. On a work/review page, first collect hidden inputs because global variables can be missing:

```js
var params = Array.from(document.querySelectorAll("input[type=hidden]")).reduce((result, input) => {
  if (input.name) result[input.name] = input.value;
  return result;
}, {});
params;
```

Then trigger packaging from a logged-in page:

```js
new Promise((resolve) => {
  $.ajax({
    type: "get",
    url: "/mooc2-ans/work/packWork",
    data: {
      courseid: params.courseid || params.courseId,
      clazzid: params.clazzid || params.clazzId || params.currentClassId,
      workid: params.workid || params.workId,
      type: 0,
      // uid: often undefined — omit if not available
      // fid: not in hidden inputs — supply from known value (e.g., "1971") or omit
      onlyattachment: "0",     // 0=word export, 1=only attachments
      taskId: params.taskId,   // omit if undefined
      isPdf: "0",              // 0=word, 1=pdf
      packtype: "1",
      customNameGroup: "",
      wordCustomFormat: "",
      personIds: "",           // empty = all students
    },
    success: data => resolve(data),
    error: xhr => resolve({ error: xhr.status }),
  });
});
```

Note: `uid` and `fid` are often absent from hidden inputs. `uid` can be omitted entirely (the API doesn't require it). For `fid`, extract it from the course URL or the teacher's known `fid` value — it is the second path segment in the download URL (e.g., `workzip/FID/...`). The review page URL also contains `cpi` which can be used to look up the user, but `fid` is not encoded there.

The `onlyattachment` and `isPdf` parameters control export format:
- `onlyattachment="1", isPdf="1"` → PDF export of attachments
- `onlyattachment="0", isPdf="0"` → Word (.docx) export of reports  
- `onlyattachment="1", isPdf="0"` → attachment files only (original uploaded files)
- Omit `uid` and `taskId` entirely if they are undefined — the API handles missing fields gracefully.

After about 15 seconds, inspect the download center and pick the newest `workzip` URL whose `fn=` filename matches the target assignment:

```js
new Promise((resolve) => {
  $.ajax({
    url: "/mooc2-ans/tcm/downloadcenter",
    data: { courseId: params.courseid || params.courseId, pageNum: 1, cpi: params.cpi, order: "down" },
    dataType: "html",
    success: html => resolve(html),
    error: xhr => resolve("ERROR " + xhr.status),
  });
});
```

Download with cookies and extract with the script:

```bash
curl -L -b cx_cookies.txt -o output.zip "DOWNLOAD_URL" -H "User-Agent: Mozilla/5.0"
python scripts/extract_work_zip.py output.zip -d output_dir
```

`scripts/extract_work_zip.py` uses GBK filename fallback and safe path extraction. `scripts/batch_grade.py` also expands common "one zip per student" folders, so run it on the extracted parent directory rather than manually flattening files.

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
- `format`: `docx`, `doc`, or `none`
- `expanded_zip`
- `report_path`
- `preview`
- `section_signal`
- `reflection_signal`

Material-reading behavior implemented by `scripts/batch_grade.py`:

- `.docx`: reads both paragraphs and table cells. Chaoxing experiment report templates often store most content in tables; paragraph-only extraction is misleading.
- `.doc`: best-effort OLE2 text extraction.
- templates: filters likely blank templates containing `V2024`, `模板`, or `template` before falling back to any `.docx`.
- nested archives: expands per-student zip files into `__unzipped__`.
- image count: exact for `.docx`; estimated for `.doc` from file size, with files over about 500 KB treated as likely image-bearing.
- `too_short` means a readable report exists but is below `--min-chars`; it is not the same as `missing_report`.

### 8. Draft Scores

Before drafting scores, confirm the score range and scoring mode. For `concise` or `detailed` modes, start with 3-5 representative submissions and calibrate the rubric with the teacher. After the teacher accepts the rubric, continue with the rest.

For `random` mode, skip calibration from submissions because assignment content is intentionally not inspected. Still show the teacher the planned score range, randomization method, and final score list before any write.

Use `--sample 5` or a manual spread across early/middle/late submissions for calibration. Report the sample in a compact table before drafting the full score list:

```text
student_id | student_name | chars | images | sections | reflection | status | provisional_band | notes
```

Ask the teacher to choose or adjust the grading posture before full scoring:

- lenient: best work can receive 100, most complete submissions are 85-95, and routine completed work should usually not fall below 70-75. When the teacher says "这只是作业不是考试" (this is homework not an exam), err toward the upper end of each band — they want students to feel rewarded, not penalized.
- strict: keep 100 for clearly excellent work and spread ordinary submissions across 70-95.

The teacher's particular grading philosophy for experiment reports:
- "步骤空白是好空白" — blank 实验步骤与结果 sections do NOT automatically mean low quality. Students often paste screenshots directly into the docx rather than writing text. The presence of unique embedded screenshots (check via docx zip analysis) counts as valid process documentation.
- Missing/wrong 总结 (reflection) is a heavier penalty than blank steps, because the reflection evaluates understanding while screenshots prove the work was done.
- Multiple students scoring 100 is acceptable — "这只是作业不是考试" (it's homework, not an exam). Don't artificially compress the high end.
- Lowest scores should generally not fall below 70-75 for submitted work.

Conservative report-grading posture:

- 90-100: complete report, correct task match, clear process/results, screenshots or evidence, source/code when required
- 80-89: mostly complete, minor omissions in analysis, screenshots, or conclusions
- 70-79: task covered but important evidence, code, or explanation is missing
- 60-69: minimal completion with weak report or incomplete evidence
- below 60: major missing artifacts, irrelevant submission, empty content, or confirmed serious issue

For experiment-report assignments, a useful starting rubric is (see `references/scoring-methodology.md` for a complete Python formula that maps batch_grade metrics to scores):

- section completeness: 20%
- text substance inside report/table cells: 15%
- process and result detail: 25%
- screenshot/code/result evidence: 20%
- conclusion or reflection quality: 10%
- format and header completeness: 10%

For teacher-facing messages, use the current Chinese Markdown score table template from `references/steps/05-draft-scores.md`. Do not paste raw CSV or raw metric strings as the default response.

Use this fixed score-draft schema for scripts, saved artifacts, or teacher-requested audit data:

```csv
student_id,student_name,score,band,evidence,penalty_reason,needs_manual_review,workAnswerId
```

Scoring rules that must stay explicit:

- Every `score` must be inside the teacher-confirmed score range.
- `random` mode evidence must state that assignment content was not inspected; do not invent content-based reasons.
- `needs_manual_review=true` when the report remains unreadable after direct agent-side file inspection, or when it is missing, suspiciously duplicated, image-heavy but not inspected, or mismatched to the assignment. For unreadable reports, the agent must first open and inspect alternate report candidates, nested archives/attachments, and available PDF/original-attachment packages before asking the teacher to review. Rerunning a material-prep script is not sufficient confirmation.
- Do not assign below 70 to a submitted experiment report unless the evidence column states the major defect.
- Do not assign 100 unless the evidence column states why it is complete enough for full credit.
- Keep similar submissions within a narrow score range unless a concrete difference is documented.
- If the teacher has not accepted the calibration posture, output score suggestions only and do not prepare a write action.

Quality checks before finalizing scores:

- Image-heavy submissions can have low text but strong evidence; inspect screenshots instead of scoring only by `char_count`.
- **CRITICAL: "Blank" 步骤与结果 sections do not mean empty submissions.** Students often paste screenshots directly into the docx rather than writing text. The `batch_grade.py` script only extracts text — it cannot read embedded images. When `char_count` is low and `img_count` is non-zero, investigate the images before grading:
  1. Open the `.docx` as a zip and list `word/media/`:
     ```python
     import zipfile
     with zipfile.ZipFile(report_path) as z:
         imgs = [n for n in z.namelist() if n.startswith('word/media/')]
     ```
  2. Separate template images from student-generated screenshots by comparing sizes or hashes across students. The common template logo/header image (~77KB) is often identical across all submissions — filter it out.
  3. The remaining unique images (screenshots of code, terminal output, PyCharm windows) are evidence the student ran the experiment. Count these as valid process documentation even if text cells are empty.
  4. Reports with unique screenshots but blank text cells should still be marked down if the reflection/summary is also missing — the images prove the work was done, but the reflection evaluates understanding.
- Some submissions contain content but omit numbered section headings; search for keywords before treating a section as missing.
- Files with identical sizes or near-identical previews across a group are suspicious; inspect them together and keep scoring consistent.
- Garbled filenames do not imply garbled document content.

### 9. Batch Scoring from the List Page (Recommended)

The review list page (`/mooc2-ans/work/mark?...`) has a score textbox for each student row. **Typing a score and pressing Tab (blur) auto-saves via AJAX** — no need to open individual review pages.

Quick batch workflow (for 20+ submissions):

```js
// Collect all score inputs on the current page
var inputs = document.querySelectorAll('input.questionScore');
var studentRows = Array.from(inputs).map((input, i) => ({
  input: input,
  row: input.closest('li') ? input.closest('li').parentElement : null,
}));

// Fill scores from a mapping: { studentName: score }
var scores = { '周馨瑶': 85, '张雪茹': 86 };
studentRows.forEach(item => {
  var nameEl = item.row ? item.row.querySelector('li:nth-child(2)') : null;
  if (!nameEl) return;
  var name = nameEl.innerText.trim();
  if (scores[name] !== undefined) {
    item.input.value = scores[name];
    item.input.dispatchEvent(new Event('input', { bubbles: true }));
    item.input.dispatchEvent(new Event('change', { bubbles: true }));
    item.input.dispatchEvent(new Event('blur', { bubbles: true }));
  }
});
```

After filling all scores on the current page, navigate to the next page (click page number `2`) and repeat. No save button needed — blur event auto-submits each score.

### Preferred: Export → Edit → Import (Batch)

**⚠️ 全提交约束：此方法仅当全班同学都已提交作业时才可使用。**
如果有未提交的学生，导出模板包含所有学生行，导入时会将这些未交学生的状态从"未交"改为"已完成/待重做"，导致虚假评分。导入API会处理XLS中的每一行——即使是空分数行。

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

**选择策略：**
- ✅ 全班已提交 → 使用 Export→Edit→Import 方法（最高效）
- ❌ 有未交学生 → 使用列表页直接输入分数+Tab保存的方法（见下方「Alternative: Direct Input on List Page」），或先将未交学生从XLS中筛除再导入

This is the **most efficient** method for 20+ submissions when ALL students have submitted. Works via live browser or curl.

**Step 1 — Export**: Click `Export grades` (导出成绩) on the review list page, or call the API:

```bash
# Get the enc from the page: $('#workScoreExportEnc, #enc').val()
MOOC_URL="https://mooc1.chaoxing.com/import-export-ans"
curl -L -b cx_cookies.txt -o scores.xls \
  "$MOOC_URL/export-workscore?courseId=COURSEID&classId=CLAZZID&workId=WORKID&mooc=1&isTemplate=false&cpi=CPI&enc=ENC&addLog=true"
```

The exported XLS has columns: **A**=学号, **B**=姓名, **I**=分数, **Q**=简答题得分; **J**=状态 (e.g., "待批" or "未交").

**Step 2 — Edit**: Modify the XLS using openpyxl.

**⚠️ CRITICAL: Filter out unsubmitted students.** The import API processes ALL rows in the XLS. If a student whose status is "未交" (unsubmitted) has an empty score cell, the API will mark them as "Completed" with score 0 — effectively turning them into a submitted-and-reviewed student. NEVER modify or include rows where column J (status) contains "未交". Skip them in your score loop:

```python
import openpyxl, shutil
wb = openpyxl.load_workbook('scores.xlsx')  # the .xls is actually xlsx
ws = wb.active
score_map = {'233080461': 98, ...}  # your scores

for row in range(4, ws.max_row + 1):  # data starts at row 4
    status = str(ws.cell(row, 10).value or '').strip()  # column J
    if '未交' in status:
        continue  # SKIP unsubmitted students — do not touch their cells
    sid = str(ws.cell(row, 1).value or '').strip()
    if sid in score_map:
        ws.cell(row, 9).value = score_map[sid]   # I: 分数
        ws.cell(row, 17).value = score_map[sid]  # Q: 简答题得分

# IMPORTANT: save as .xlsx first, then copy to .xls for import
# openpyxl saves OOXML content regardless of extension, but
# openpyxl.load_workbook() checks the extension and will refuse
# to re-read a .xls file even with valid OOXML content.
wb.save('scores_modified.xlsx')
shutil.copy('scores_modified.xlsx', 'scores_modified.xls')
```

**Step 3 — Import**: Upload via the import API:

```bash
# Get the import enc: $('#enc').val() (different from export enc!)
curl -L -b cx_cookies.txt \
  -F "iframeFileName=@scores_modified.xls" \
  "$MOOC_URL/import/importScore?workId=WORKID&courseid=COURSEID&classid=CLAZZID&enc=IMPORT_ENC&cpi=CPI&ipAddress=YOUR_IP"
```

Expected response: `{"status":true}`. The page auto-reloads on success.

**Caveat**: The import API only accepts `.xls` extension (checked by regex), but actually accepts OOXML content. Save with `.xls` extension even if the content is xlsx.

#### Recovery: Fix unsubmitted students marked by a bad import

If you already imported and unsubmitted students show as "Completed" (完成) with score 0 instead of "未交", use the `batchBack` API to return them to "待重做" (pending redo) status. The endpoint is:

```bash
curl -s -b cx_cookies.txt \
  "https://mooc2-ans.chaoxing.com/mooc2-ans/work/batchBack?backAnswerIdsStr=ID1,ID2,ID3" \
  -d "courseid=COURSEID&clazzid=CLAZZID&cpi=CPI&workid=WORKID&answerIds=ID1,ID2,ID3&reason=作业过期未提交，打回重做&extraTime=2026-05-25 23:59"
```

Parameters:
- `answerIds` / `backAnswerIdsStr`: comma-separated `workAnswerId` values for the unsubmitted students. Find these from the review page: query `a[onclick*="rebackOne"]` and extract the numeric ID from `rebackOne(12345)`.
- `reason`: text shown to the student as the return reason.
- `extraTime`: **required** when the assignment has expired. Must be a future deadline string like `"2026-05-25 23:59"`. Without this, the API rejects with a "请输入截止时间" toast.

Expected success response: `{"msg":"打回成功","status":true}`. After calling, re-export to verify the status column shows "待重做" instead of "完成".

### Alternative: Direct Input on List Page

Alternatively, type scores directly into the score textboxes on the list page and press Tab — it auto-saves via AJAX blur event.

### Fallback: Individual Review-Page Submission

If the above methods don't work, fall back to individual review-page submission:

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

The submit helper validates CSV rows and builds review URLs from `courseid`, `clazzid`, `work-id`, and `workAnswerId`. It requires a browser automation Python environment that provides `cdp(...)` and `js(...)` before `--confirm-submit` can write scores.

If the terminal environment lacks `cdp()`/`js()` (e.g., running via terminal tool rather than a browser-harness Python session), use the Playwright fallback approach documented in `references/playwright-submit-fallback.md`. Install Playwright (`pip install playwright && python3 -m playwright install chromium`) and author a standalone script that loads cookies and navigates each review URL programmatically.

Page-write behavior in `scripts/batch_submit_scores.py` intentionally mirrors the old reliable flow:

- navigate to each `review-work` URL
- set visible `input.questionScore`
- trigger `input`, `change`, `keyup`, and `blur`
- set hidden `#tmpscore`
- set hidden `#score`
- call `markAction(1)`

If manual recovery is needed, use the same sequence; setting only the visible input is not enough on many Chaoxing pages.

When there are more than 20 submissions, collect `workAnswerId` across pages from the review list before building the CSV:

```js
searchMarkList(2);
```

After submission, verify status changed from "To be reviewed" to "Completed" or the corresponding Chinese status. If it did not, suspect an empty `tmpscore`, stale `workAnswerId`, or a class-context mismatch.

## Pitfalls

- **⚡ 导入XLS会误改未交学生状态（关键）**: 导出成绩的XLS包含所有学生行（包括未交的）。导入时即使不填分数，这些空行也会被处理，导致未交学生的状态从"未交"变为"已完成"（甚至被赋予0分）。修复方法：调用打回API将他们恢复到"待重做"状态：
  ```bash
  # 收集未交学生的 workAnswerId，然后批量打回
  answerIds="ID1,ID2,ID3,..."
  curl -s -b cx_cookies.txt \
    "https://mooc2-ans.chaoxing.com/mooc2-ans/work/batchBack?backAnswerIdsStr=$answerIds" \
    -d "courseid=COURSEID&clazzid=CLAZZID&cpi=CPI&workid=WORKID&answerIds=$answerIds&reason=打回重做&extraTime=2026-06-01 23:59" \
    -H "X-Requested-With: XMLHttpRequest"
  ```
  **最佳实践：有未交学生时，不要用导入法，改用列表页直接输入分数+Tab保存的方法。**

- **Session expiration is frequent**: The browser session on mooc2-ans.chaoxing.com expires frequently (~5 min idle). Every navigation to a new URL may redirect to login. For reliable operations, prefer curl with cookie file for API calls rather than browser navigation. Keep the cookie file refreshed via `chaoxing_login_cookie.py` before long operations.
- **openpyxl save-as-.xls load trap**: `openpyxl.save('scores.xls')` writes OOXML content despite the `.xls` extension, but `openpyxl.load_workbook('scores.xls')` checks the extension and refuses to load files ending in `.xls`. If you need to re-read the modified file (e.g. for verification), save as `.xlsx` first, then `shutil.copy` to `.xls` for the import API. The import API checks only the filename regex, not the content format.
- **Export enc ≠ Import enc**: The "Export grades" button uses a value from hidden input `#workScoreExportEnc`, but the "Import the score" API uses a different value from hidden input `#enc`. These are different enc values! Always collect both from the page before attempting import:
  ```js
  var exportEnc = $('#workScoreExportEnc').val();  // for export API
  var importEnc = $('#enc').val();                  // for import API
  ```
- **Import only accepts `.xls` filename**: The import JS function checks `fileName.match(/.*(?=xls$)/)` — only filenames ending in `.xls` pass. However, the actual content can be OOXML (xlsx format). Save modified files with `.xls` extension even if the content is xlsx.
- **Exported file is OOXML despite `.xls` extension**: The export download is named `.xls` but is actually OOXML format (recognized by `file` command as "Microsoft Excel 2007+"). Use `openpyxl` to read/write it, and save with `.xls` extension for re-import compatibility.
- **Python environment mismatch**: openpyxl, playwright, and other pip packages may be installed in the system Python (`/usr/bin/python3`) rather than the Hermes venv Python. Check with `which python3` and install in the correct one. Use `/usr/bin/python3` explicitly if needed.
- **Playwright cookie injection**: When using Playwright for automation, load cookies from the MozillaCookieJar file and inject via `context.add_cookies()`. The browser's own cookie jar may not persist across page navigations to different Chaoxing subdomains.
- **The "More" dropdown hides the import button**: Clicking `More` () opens a dropdown with "Import the score" and "Export homework". The dropdown closes on second click or if you interact elsewhere. Click `More` first, then immediately click the import link.
- Initial work list URL with a `clazzid` from a different class will show that class's assignments. If the target assignment isn't visible, always check the class switcher first — the `clazzid` in the URL may be stale from a previous navigation.
- Do not rely only on global variables such as `courseId`; Chaoxing often stores needed values in hidden inputs or link `data` attributes.
- The work list's review action commonly appears as `a[onclick*="toMarkWork"]` with a `data="/mooc2-ans/work/library/review-work?...` URL. Match the parent row text to the assignment title before clicking.
- The class switcher commonly uses `li.classli`; direct `selectClassid=...` URLs are often more reliable than UI clicks when the class id is known.
- For export, `packWork` can return a background-processing response; wait and check `downloadcenter` instead of repeatedly clicking export.
- The newest download-center `workzip` item is usually first, but confirm the URL filename (`fn=`) matches the target assignment.
- `vc3` and `p_auth_token` are httpOnly cookies; use the cookie file or CDP-style injection, not `document.cookie`.
- For `.docx`, read paragraphs and table cells.
- For `.doc`, text extraction is best-effort and image count is an estimate.
- Short parsed reports are `too_short`, not `missing_report`.
- Do not grade image-heavy reports from text length alone.
- Do not submit scores until the teacher has seen the exact score list and explicitly confirmed it.
- Do not commit cookies, downloaded submissions, generated reports, or score CSVs containing student data unless explicitly requested.

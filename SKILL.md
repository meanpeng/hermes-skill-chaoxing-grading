---
name: chaoxing-assignment-grading
description: "Use when grading Chaoxing/Xuexitong assignments. Teacher workflow: login, reliably find courses/classes/assignments with Chaoxing page selectors, inspect submissions, organize exported materials, draft scores, and submit only after explicit confirmation."
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

Assignment discovery on the work list page should be DOM-driven. Extract candidate rows before clicking:

```js
Array.from(document.querySelectorAll("a[onclick*='toMarkWork'], a[data*='review-work'], a[href*='work']")).map(a => {
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

### 5. Inspect Submissions

Open one student's review page before batch work. Read:

- answer text
- attachments and previews
- student name / id / class
- score boxes and comment boxes

Do not fill scores or comments unless the teacher has confirmed that exact change.

### 6. Export And Organize Attachments

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
      uid: params.uid,
      fid: params.fid,
      onlyattachment: "1",
      taskId: params.taskId,
      isPdf: "1",
      packtype: "1",
      customNameGroup: "",
      wordCustomFormat: "",
      personIds: "",
    },
    success: data => resolve(data),
    error: xhr => resolve({ error: xhr.status }),
  });
});
```

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

### 7. Draft Scores

Start with 3-5 representative submissions and calibrate the rubric with the teacher. After the teacher accepts the rubric, continue with the rest.

Use `--sample 5` or a manual spread across early/middle/late submissions for calibration. Report the sample in a compact table before drafting the full score list:

```text
student | chars | images | sections | reflection | status | notes
```

Ask the teacher to choose or adjust the grading posture before full scoring:

- lenient: best work can receive 100, most complete submissions are 85-95, and routine completed work should usually not fall below 70-75.
- strict: keep 100 for clearly excellent work and spread ordinary submissions across 70-95.

Conservative report-grading posture:

- 90-100: complete report, correct task match, clear process/results, screenshots or evidence, source/code when required
- 80-89: mostly complete, minor omissions in analysis, screenshots, or conclusions
- 70-79: task covered but important evidence, code, or explanation is missing
- 60-69: minimal completion with weak report or incomplete evidence
- below 60: major missing artifacts, irrelevant submission, empty content, or confirmed serious issue

For experiment-report assignments, a useful starting rubric is:

- section completeness: 20%
- text substance inside report/table cells: 15%
- process and result detail: 25%
- screenshot/code/result evidence: 20%
- conclusion or reflection quality: 10%
- format and header completeness: 10%

Quality checks before finalizing scores:

- Image-heavy submissions can have low text but strong evidence; inspect screenshots instead of scoring only by `char_count`.
- Some submissions contain content but omit numbered section headings; search for keywords before treating a section as missing.
- Files with identical sizes or near-identical previews across a group are suspicious; inspect them together and keep scoring consistent.
- Garbled filenames do not imply garbled document content.

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

The submit helper validates CSV rows and builds review URLs from `courseid`, `clazzid`, `work-id`, and `workAnswerId`. It requires a browser automation Python environment that provides `cdp(...)` and `js(...)` before `--confirm-submit` can write scores.

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

- Current class context is easy to lose. Always confirm class name and counts on the review list.
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

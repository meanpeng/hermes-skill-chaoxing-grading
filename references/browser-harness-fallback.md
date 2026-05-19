# Browser Harness Fallback

Use this only after the matching script failed or Chaoxing changed page/API structure. The fallback is still governed by `references/agent-rules.md`: browser snippets do not grant permission to open submissions, export/download materials, write scores, import grade files, return work, or click final submit buttons.

## Failure Triage

Record the failed script command, exit status, and the first useful error line before switching to Browser harness. Choose the narrowest fallback:

```text
failed_command: <command>
failure_class: cookie | discovery | download | material-prep | submit | verify
safe_next_browser_action: read-only | download-after-setup-confirmation | write-after-final-confirmation
fallback_evidence_to_collect: url | selectors | hidden inputs | network endpoint | exported table
```

Do not use Browser harness to bypass a workflow gate. If the script failed before the gate was satisfied, the browser route is limited to the same safe phase.

## Cookie And Session Fallback

If `check_cookie.py` cannot prove the cookie but the teacher is already logged in inside the browser, use the current tab as the source of truth and navigate with CDP instead of attempting `document.cookie`; Chaoxing auth cookies such as `vc3` and `p_auth_token` can be `httpOnly`.

```python
cdp("Network.enable")
cdp("Page.navigate", url="https://i.chaoxing.com")
```

Valid session evidence:

```js
({
  url: location.href,
  title: document.title,
  loggedInSignals: Array.from(document.querySelectorAll("a,span,div"))
    .map(el => el.innerText.trim())
    .filter(Boolean)
    .slice(0, 30)
})
```

If a browser helper reports `Unknown Target method: activateTarget`, reuse the current real tab and call `Page.navigate`.

## Read-Only Discovery Fallback

Use this when `chaoxing_discover.py` cannot parse the course or assignment list. Discovery must stay read-only: do not open individual student submissions and do not export/download.

Open the personal space or teacher course page:

```python
cdp("Page.navigate", url="https://i.chaoxing.com")
```

Collect course candidates:

```js
Array.from(document.querySelectorAll("a"))
  .map(a => ({ text: a.innerText.trim(), href: a.href }))
  .filter(x =>
    x.text.length > 1 &&
    (/courseid|courseId|mycourse|interaction/.test(x.href))
  );
```

Open a known work list when `courseid`, `clazzid`, and `cpi` are known:

```python
cdp(
  "Page.navigate",
  url="https://mooc2-ans.chaoxing.com/mooc2-ans/work/list?courseid=COURSEID&selectClassid=CLAZZID&cpi=CPI&status=-1&v=0&topicid=0",
)
```

Extract visible assignments and candidate `workId` values:

```js
Array.from(document.querySelectorAll("a[onclick*='toMarkWork'], a[href*='work/mark'], a"))
  .map(a => {
    const row = a.closest("tr,li,.workList,.work-list,div") || a.parentElement;
    const data = a.getAttribute("data") || a.getAttribute("onclick") || a.href || "";
    const text = row ? row.innerText.trim() : a.innerText.trim();
    const workId = (data.match(/workId=(\d+)/i) || data.match(/workid['":,\s]+(\d+)/i) || [])[1] || "";
    return { text, href: a.href, data, workId };
  })
  .filter(x => x.workId || /已交|未交|待批|批阅|作业/.test(x.text));
```

On the review list, collect rows without opening submissions:

```js
Array.from(document.querySelectorAll("a[onclick*='toMarkWork'], a[href*='review'], input.scoreInput"))
  .map(el => {
    const row = el.closest("tr,li,.stu-list,.mark-item,div") || el.parentElement;
    const data = el.getAttribute("data") || el.getAttribute("onclick") || el.href || "";
    const workAnswerId = (data.match(/workAnswerId=(\d+)/i) || data.match(/workAnswerId['":,\s]+(\d+)/i) || [])[1] || "";
    return { workAnswerId, rowText: row ? row.innerText.trim() : el.outerHTML.slice(0, 300), data };
  })
  .filter(x => x.workAnswerId || x.rowText);
```

Report browser evidence with the current URL, visible class name, assignment title, submitted count, pending-review count, and unsubmitted count.

## Download/Export Fallback

Use this only after the teacher has confirmed `concise` or `detailed` scoring and the exact target assignment. Skip this section for `random` mode.

From the work list or review page, collect hidden inputs:

```js
Array.from(document.querySelectorAll("input[type=hidden]")).reduce((result, input) => {
  if (input.name || input.id) result[input.name || input.id] = input.value;
  return result;
}, {});
```

Trigger package creation from the logged-in page:

```js
new Promise(resolve => {
  $.ajax({
    type: "get",
    url: "/mooc2-ans/work/packWork",
    data: {
      courseid: "COURSEID",
      clazzid: "CLAZZID",
      workid: "WORKID",
      type: 0,
      onlyattachment: "0",
      isPdf: "0",
      packtype: "1",
      customNameGroup: "",
      wordCustomFormat: "",
      personIds: "",
    },
    success: data => resolve({ ok: true, data }),
    error: xhr => resolve({ ok: false, status: xhr.status, text: xhr.responseText }),
  });
});
```

Then open the download center and collect package links:

```python
cdp(
  "Page.navigate",
  url="https://mooc2-ans.chaoxing.com/mooc2-ans/tcm/downloadcenter?courseId=COURSEID&pageNum=1&cpi=CPI&order=down",
)
```

```js
Array.from(document.querySelectorAll("a"))
  .map(a => ({ text: a.innerText.trim(), href: a.href }))
  .filter(x => /workzip|download|zip|下载/.test(x.href + " " + x.text));
```

Download the chosen URL with the already validated cookie file, then return to the normal extraction scripts:

```bash
curl -L -b cx_cookies.txt -o output.zip "DOWNLOAD_URL" -H "User-Agent: Mozilla/5.0"
python scripts/prepare_work_materials.py --zip-file output.zip --output-dir prepared/output --mode metrics
```

## List-Input Submit Fallback

Prefer `scripts/submit_scores.py`. Use Browser harness write fallback only when that script cannot parse/write the list page and the teacher has explicitly confirmed the exact final write plan in the current turn.

Required state:

```text
teacher_confirmed_exact_score_list: yes
score_range_confirmed: yes
target course/class/assignment verified: yes
student_count_to_write: <n>
manual_review_remaining: 0
unsubmitted_count: <n>
```

First capture row selectors and `workAnswerId` values:

```js
Array.from(document.querySelectorAll("input.scoreInput, input.inp80.scoreInput"))
  .map(input => {
    const row = input.closest("tr,li,.stu-list,.mark-item,div") || input.parentElement;
    return {
      value: input.value,
      name: input.name,
      id: input.id,
      workAnswerId:
        input.getAttribute("data") ||
        input.getAttribute("data-answerid") ||
        ((row && row.innerHTML.match(/workAnswerId[='":,\s]+(\d+)/i)) || [])[1] ||
        "",
      rowText: row ? row.innerText.trim() : "",
    };
  });
```

For each confirmed target row, set the visible input and dispatch the same browser events a teacher edit would fire:

```js
async function setScoreInput(input, score) {
  input.focus();
  input.value = String(score);
  ["input", "change", "keyup", "blur"].forEach(type => {
    input.dispatchEvent(new Event(type, { bubbles: true }));
  });
  await new Promise(resolve => setTimeout(resolve, 500));
  return { value: input.value };
}
```

After each row, inspect the page or network response for failure text. Stop on the first mismatch or validation error. Do not click `提交`, `提交并进入下一份`, `完成`, or `打回重做` unless that exact button action was part of the confirmed write plan.

## Individual Review Submit Fallback

Use `references/playwright-submit-fallback.md` for individual review-page submission. That path is riskier than list-input because it enters one submission at a time and can trigger final buttons. It requires `workAnswerId` for every row and explicit teacher confirmation.

## Verification Fallback

Prefer `scripts/verify_score_export.py`. If it cannot find `workScoreExportEnc`, use Browser harness to collect hidden export fields from the review page:

```js
Array.from(document.querySelectorAll("input[type=hidden]")).reduce((result, input) => {
  if (/enc|Export/i.test(input.name + input.id)) result[input.name || input.id] = input.value;
  return result;
}, {});
```

If the export URL is visible in the page scripts, collect likely endpoints:

```js
Array.from(document.scripts)
  .map(s => s.textContent)
  .join("\n")
  .match(/.{0,80}(export-workscore|workScoreExportEnc|import-export-ans).{0,120}/g);
```

Download the exported workbook only when it is needed for verification. Compare:

```text
student_id | expected_score | browser_list_score | exported_score | status | match
```

Report mismatches before retrying any write. A verification fallback is allowed to read the list and exported grade table; it is not permission to modify scores again.

## Stop Conditions

Stop the Browser harness fallback and return to the teacher when:

- the page asks for login or captcha and no valid session is available
- candidate course/class/assignment cannot be distinguished safely
- counts differ from the ledger
- a selector matches more or fewer rows than the confirmed score list
- a write response is missing, ambiguous, or reports an error
- exported verification does not match the submitted scores


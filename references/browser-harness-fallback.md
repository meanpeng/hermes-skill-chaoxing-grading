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

## Per-Step Fallback Principle

Each workflow step (discovery, download, submit, verify) should **first attempt the script path**, and fall back to browser operations **only if the script fails**. This is not a global decision — a script failure in one step does not imply the next step will also fail. After completing a browser-fallback step, the **next step must again try the script path first**.

Correct pattern:

```text
Step 1: run discovery script → success → use script results
Step 2: run download script → FAIL → fall back to browser packWork + curl download
Step 3: run submit script → success → use script, no browser needed
Step 4: run verify script → success → use script
```

Incorrect pattern (do not do this):

```text
Step 1: discovery script → FAIL → enable browser for ALL remaining steps
```

The cookie file and script environment are independent of browser state. A script that works for discovery may also work for download even if discovery appears to have failed due to a transient parsing issue. Always reset to script-first at the start of each phase.

## Cookie And Session Fallback

If `check_cookie.py` cannot prove the cookie but the teacher is already logged in inside the browser, use the current tab as the source of truth and navigate with CDP instead of attempting `document.cookie`; Chaoxing auth cookies such as `vc3` and `p_auth_token` can be `httpOnly`.

### Cookie Valid, Browser Blocked

A common scenario: every Chaoxing URL redirects to `passport2.chaoxing.com/login` in the browser, but `check_cookie.py --cookie-file ./cx_cookies.txt` reports `status=200`. This is not a session failure — the browser environment simply lacks cookie injection (no CDP `Network.setCookie` available), while the MozillaCookieJar-backed scripts remain fully operational.

When this mismatch is confirmed (browser → login, check_cookie → valid), **do not attempt to work around the browser block by credential entry or CAPTCHA**. Instead, treat the script path with `--cookie-file ./cx_cookies.txt` as the primary fallback for every phase:

| Phase | Script to use | Cookie source |
|---|---|---|
| Discovery | `chaoxing_discover.py --cookie-file ./cx_cookies.txt` | `--cookie-file` |
| Download | `download_work_zips.py --cookie-file ./cx_cookies.txt ... --confirm-download` | `--cookie-file` |
| Material prep | `prepare_work_materials.py` (from downloaded zip, no cookie needed) | N/A |
| Submit | `submit_scores.py --cookie-file ./cx_cookies.txt ... --confirm-submit` | `--cookie-file` |
| Verify | `verify_score_export.py --cookie-file ./cx_cookies.txt` | `--cookie-file` |

The browser fallback JS selectors documented below (workAnswerId extraction, score input, hidden export fields) remain the **reference pattern** for environments that DO support cookie injection. In a cookie-injection-capable environment (Playwright with cookie jar loading), navigate after injecting `cx_cookies.txt` cookies via CDP:

```python
# Playwright pattern: load MozillaCookieJar, set for domain, then navigate
import http.cookiejar
jar = http.cookiejar.MozillaCookieJar("./cx_cookies.txt")
jar.load(ignore_discard=True, ignore_expires=True)
for c in jar:
    context.add_cookies([{
        "name": c.name, "value": c.value,
        "domain": c.domain, "path": c.path,
        "httpOnly": "HttpOnly" in str(c._rest),
        "secure": c.secure,
    }])
page.goto("https://mooc2-ans.chaoxing.com/mooc2-ans/work/mark?...")
```

If the current browser environment lacks cookie injection AND the scripts work, do not chase a browser-mediated approach. Report both facts (browser → login, cookie → valid) and proceed with script-path commands.

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

### Browser Session Persistence Warning

**The browser session is fragile.** In Hermes' browser environment, navigating away from a Chaoxing page — even to `about:blank` — can destroy the authentication cookies and leave the browser redirected to `passport2.chaoxing.com/login` on the next Chaoxing URL. Known triggers:

- Navigating to `about:blank` or a non-Chaoxing domain
- Page reload triggered by "Export grades", "More", or class tab switch
- Any `browser_navigate` that causes a full page unload before the new URL loads

**Mitigation**: If the browser was logged in manually (credentials entered in the browser), keep all navigation within `mooc2-ans.chaoxing.com` and `i.chaoxing.com`. Do not navigate to `about:blank`, local files, or unrelated URLs between Chaoxing operations. If the session is lost, re-login or fall back to the script path with `--cookie-file`.

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

### Collect Parameters for packWork

The review page has **no** `input[type=hidden]` elements. Extract `courseid`, `clazzid`, and `workId` from the Review link's `data` attribute instead:

```js
var link = document.querySelector('a[onclick="toMarkWork(this)"]');
var data = link.getAttribute('data') || '';
var params = {};
data.replace(/[?&]([^=]+)=([^&]+)/g, function(_, k, v) { params[k] = decodeURIComponent(v); });
// → params.courseid, params.clazzid, params.workId
```

If the review page hasn't been loaded yet, use the known values from the discovery phase.

### Trigger Package Creation

From the logged-in page, call the packWork API via jQuery:

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

### Async Processing Notice

`packWork` is **asynchronous for packages larger than a few MB**. The response will indicate background processing:

```json
{"status":"1","msg":"如果下载的附件较大，会转入后台处理，请持续关注此按钮显示，系统处理时间最多不超过12小时。"}
```

The download center may not show a completed package link immediately. Poll by re-navigating or refreshing:

```python
import time
# Wait 10-30 seconds for large packages, then re-open the download center
cdp("Page.navigate",
  url="https://mooc2-ans.chaoxing.com/mooc2-ans/tcm/downloadcenter?courseId=COURSEID&pageNum=1&cpi=CPI&order=down")
```

If the package was previously created in an earlier session, the download link will appear immediately without a new packWork call. You can skip the AJAX trigger and go straight to the download center.

### Collect Download URLs

Navigate to the download center and collect package links:

```python
cdp(
  "Page.navigate",
  url="https://mooc2-ans.chaoxing.com/mooc2-ans/tcm/downloadcenter?courseId=COURSEID&pageNum=1&cpi=CPI&order=down",
)
```

The download links point to `fanyadata.chaoxing.com` with paths containing `workzip/`. Filter by domain and path rather than broad text patterns:

```js
Array.from(document.querySelectorAll("a[href*='fanyadata.chaoxing.com']"))
  .map(a => ({ text: a.innerText.trim(), href: a.href }))
  .filter(x => x.href.includes('/workzip/'));
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

### Verified DOM Structure (2026-05-20)

The review list page (`/mooc2-ans/work/mark?...`) uses the following actual DOM structure, confirmed by live browser testing:

- Score inputs are **plain `<input type="text">`** inside nested `<li>` children — NOT `input.scoreInput` or `input.inp80.scoreInput`. The page renders one `<ul>` per student row with child `<li>` elements in fixed order: `[checkbox, name, student_id, submit_time, ip, status, _, score_input, operation_links]`.
- Class tabs appear as `<a>` links with `clazzid` embedded in member `onclick` handlers; the visible class name is shown at the top.
- "Back" link at `a[onclick*="history.back"]` — navigating away discards unsaved scores.
- "Export grades" button at `link[text*="Export grades"]` — clicking triggers a page reload that resets **all** score inputs to `0`.

First capture row selectors and `workAnswerId` values from the Review links, not the input fields:

```js
Array.from(document.querySelectorAll('a[onclick="toMarkWork(this)"]'))
  .map(a => {
    const ul = a.closest('ul');
    const items = ul ? Array.from(ul.querySelectorAll('li')) : [];
    const nameEl = items[1];
    const idEl = items[2];
    const data = a.getAttribute('data') || '';
    const workAnswerId = (data.match(/workAnswerId=(\d+)/) || [])[1] || '';
    // score input is typically at items[7]
    const scoreInput = items[7] ? items[7].querySelector('input[type="text"]') : null;
    return {
      name: nameEl ? nameEl.innerText.trim() : '',
      studentId: idEl ? idEl.innerText.trim() : '',
      workAnswerId,
      scoreElementRef: scoreInput,  // pass to setScoreInput
      rowText: ul ? ul.innerText.trim().slice(0, 300) : '',
    };
  })
  .filter(x => x.workAnswerId);
```

For environments where `document.querySelectorAll` can select the inputs directly, use the type-based approach instead of position-based indexing:

```js
Array.from(document.querySelectorAll('ul li input[type="text"]'))
  .map(input => {
    const ul = input.closest('ul');
    const items = ul ? Array.from(ul.querySelectorAll('li')) : [];
    const nameEl = items[1];
    const idEl = items[2];
    // workAnswerId is NOT on the input — get it from the Review <a> sibling
    const reviewLink = ul ? ul.querySelector('a[onclick="toMarkWork(this)"]') : null;
    const data = reviewLink ? reviewLink.getAttribute('data') || '' : '';
    const workAnswerId = (data.match(/workAnswerId=(\d+)/) || [])[1] || '';
    return {
      name: nameEl ? nameEl.innerText.trim() : '',
      studentId: idEl ? idEl.innerText.trim() : '',
      value: input.value,
      workAnswerId,
    };
  })
  .filter(x => x.workAnswerId);
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

### Page Refresh Pitfall

The review list page (`/work/mark?...`) contains UI elements that trigger a **full page reload**, which instantly discards all unsaved score inputs:

- **"More" button** (` More`) — opens/closes a toolbar dropdown but sometimes reloads the page.
- **"Export grades" link** (` Export grades`) — always triggers a hard reload that resets every `<input type="text">` value to `0`.
- **Class tab switch** — clicking a different class name refreshes to that class's roster, clearing any in-progress scores.
- **"Back" link** — navigates away entirely.

**Mitigation**: Fill all scores first using browser JS (which can survive minor state changes), then submit in one contiguous batch. Do not click any toolbar element (More, Export, Back, class tabs) between filling scores and submitting. If a page refresh does occur, re-enter all scores from a saved draft before attempting submission again.

The safe batch sequence:

```js
// 1. Collect all inputs and scores from your pre-approved draft
const scoreMap = { '56485044': 82, '56485062': 80, ... };  // workAnswerId → score

// 2. Fill and dispatch events without page interaction
Array.from(document.querySelectorAll('a[onclick="toMarkWork(this)"]')).forEach(a => {
  const data = a.getAttribute('data') || '';
  const workAnswerId = (data.match(/workAnswerId=(\d+)/) || [])[1];
  if (!workAnswerId || !(workAnswerId in scoreMap)) return;
  const ul = a.closest('ul');
  const input = ul ? ul.querySelector('input[type="text"]') : null;
  if (!input) return;
  input.focus();
  input.value = String(scoreMap[workAnswerId]);
  ['input', 'change', 'keyup', 'blur'].forEach(t =>
    input.dispatchEvent(new Event(t, { bubbles: true }))
  );
});
// 3. Submit immediately — do NOT click More, Export, or navigate away
```

## Individual Review Submit Fallback

Use `references/playwright-submit-fallback.md` for individual review-page submission. That path is riskier than list-input because it enters one submission at a time and can trigger final buttons. It requires `workAnswerId` for every row and explicit teacher confirmation.

## Verification Fallback

Prefer `scripts/verify_score_export.py`. If it cannot find `workScoreExportEnc`:

**⚠️ `input[type=hidden]` does not exist on the review page (`/work/mark?...`).** The verification-fallback JSON selectors below are documented for reference but have not been confirmed on the live review page. The script path (`verify_score_export.py`) is the primary verification method.

Check page scripts for export-related endpoints instead:

```js
Array.from(document.scripts)
  .map(s => s.textContent)
  .join("\n")
  .match(/.{0,80}(export-workscore|workScoreExportEnc|import-export-ans).{0,120}/g);
```

If an export URL is found, download and compare:

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


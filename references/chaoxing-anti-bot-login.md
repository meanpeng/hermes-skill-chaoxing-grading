# Chaoxing (超星学习通) Login — Anti-Bot Bypass Example

Complete worked example of logging into a site that detects and blocks headless Chrome.

## Problem

Chaoxing passport2 server returns empty `<form></form><form></form>` in body when accessed from headless Chromium, even with UA override. jQuery loads, login.js loads, global functions exist, but no form elements render. CSS stylesheets show 0 loaded.

## Solution: Hybrid curl + CDP approach

### Step 1: Fetch login page with curl (get real HTML)

```bash
curl -sL \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36" \
  "https://passport2.chaoxing.com/mlogin?fid=&newversion=true&refer=https://i.chaoxing.com" \
  > /tmp/chaoxing_login.html
```

### Step 2: POST login API directly (bypass browser entirely)

AES encryption required. Key: `u2oh6Vu^HWe4_AES` (16 bytes, used as both key and IV in CBC mode with PKCS7 padding).

```python
from Crypto.Cipher import AES
import base64

key = iv = b"u2oh6Vu^HWe4_AES"
def encrypt(text):
    data = text.encode('utf-8')
    pad = 16 - len(data) % 16
    data += bytes([pad] * pad)
    return base64.b64encode(AES.new(key, AES.MODE_CBC, iv).encrypt(data)).decode()

# Then POST to /fanyalogin with encrypted uname + password
```

```bash
curl -s -X POST "https://passport2.chaoxing.com/fanyalogin" \
  -H "User-Agent: Mozilla/5.0 ..." \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Origin: https://passport2.chaoxing.com" \
  -d "fid=-1&uname=<ENC_PHONE>&password=<ENC_PWD>&refer=https%3A%2F%2Fi.chaoxing.com&t=true&doubleFactorLogin=0&forbidotherlogin=0&independentId=0&independentNameId=0" \
  -c /tmp/chaoxing_cookies.txt
# Returns: {"url":"https://i.chaoxing.com","status":true}
```

### Step 3: Inject cookies into browser via CDP

```python
# CRITICAL: must enable Network domain first!
cdp("Network.enable")

# Then set each cookie — httpOnly ones REQUIRE CDP, not document.cookie
cdp("Network.setCookie", name="vc3", value="...", domain=".chaoxing.com", path="/", httpOnly=True)
cdp("Network.setCookie", name="p_auth_token", value="...", domain=".chaoxing.com", path="/", httpOnly=True)
cdp("Network.setCookie", name="UID", value="47069683", domain=".chaoxing.com", path="/")
# ... all cookies from the curl cookie jar
```

### Step 4: Navigate to authenticated page

```python
cdp("Page.navigate", url="https://i.chaoxing.com")
wait_for_load()
# Should now show the user's personal space
```

## Key cookies from login response

| Cookie | httpOnly | Purpose |
|--------|----------|---------|
| `p_auth_token` | Yes | JWT auth token |
| `vc3` | Yes | Session validation |
| `uf` | No | User fingerprint |
| `UID` / `_uid` | No | User ID |
| `fid` | No | Institution ID |
| `cx_p_token` | No | Platform token |

## Post-login navigation

The Chaoxing platform uses a shell page at `i.chaoxing.com` with a main iframe (`id="frame_content"`) for content. Menu items call `setUrl()` which loads URLs into the iframe.

### Getting iframe src
```python
iframe_src = js("document.getElementById('frame_content').src")
```

### Navigating to a course
Courses are at `mooc1.chaoxing.com` or `mooc2-ans.chaoxing.com`. The course list iframe src follows the pattern:
```
https://mooc2-ans.chaoxing.com/visit/interaction?s=<session_token>
```

### Homework/Work module URLs
- **Work list**: `https://mooc2-ans.chaoxing.com/mooc2-ans/work/list?courseid=<id>&clazzid=<id>&cpi=<id>&enc=<enc>`
- **Review/mark**: `https://mooc2-ans.chaoxing.com/mooc2-ans/work/mark?courseid=<id>&clazzid=<id>&id=<work_id>&cpi=<id>`

### Batch download homework (workPacking)
On the review page, the "More" menu (`.piyue_more` link) contains "Export homework" which calls `workPacking()`. This opens `#downWorkAttachment` dialog with 3 export options:
1. **Export complete answer record** (data=0) — answers + corrections + attachments
2. **Export only document marking annotations** (data=2) — teacher annotations as zip
3. **Export only submitted attachments** (data=1) — student files as zip

## API endpoint details

- **Login**: `POST https://passport2.chaoxing.com/fanyalogin`
- **Referer header**: `https://passport2.chaoxing.com/mlogin`
- **Form fields**: fid, uname, password, refer, t, doubleFactorLogin, forbidotherlogin, independentId, independentNameId
- **t=true** means credentials are AES-encrypted (always use encryption)
- **Pack work (export)**: `GET /mooc2-ans/work/packWork` with params: courseid, clazzid, workid, type=0, uid, fid, onlyattachment (0=full, 1=attachments only, 2=annotations), taskId, isPdf (0=Word, 1=PDF), packtype=1, customNameGroup, wordCustomFormat, personIds. Returns `{"status":"1","msg":"..."}` on success.
- **Pack status check**: No dedicated status API — use download center instead.
- **Download center**: `GET /mooc2-ans/tcm/downloadcenter` with courseId, pageNum, cpi, order. Returns HTML fragment with `<a href="https://fanyadata.chaoxing.com/workzip/...">` download links. Status shown as "Export Successful" or "have expired".
- **Download center UI**: On course main page, `loadDownload(1)` opens the download center popup. File links follow pattern: `https://fanyadata.chaoxing.com/workzip/{fid}/{courseid}/{clazzid}/{hash}/{type}/{clazzid}_{workid}.zip?_enc=...&_t=...&fn=...`
- **Class filter on work/mark page**: `li.classli` elements in dropdown filter homework by class. Click to filter: `js("document.querySelectorAll('li.classli')[N].click()")`
- **Per-student attachment download (review page — no export queue)**: `GET /mooc2-ans/work/library/review-work?courseid=..&clazzid=..&workId=..&workAnswerId=..&groupId=0&from=&sort=0&order=0&status=0&pages=1&size=20&topicid=0` — the `/library/` segment is required (`/mooc2-ans/work/review-work` 404s). Student attachments appear as iframe attributes `objectid="<32-hex>" filename="<name>"` (also HTML-escaped `&quot;` variants).
- **Resolve object → download URL**: `GET https://mooc2-ans.chaoxing.com/ananas/status/<objectid>` with header `Referer: https://mooc2-ans.chaoxing.com/...` — no Referer = 403. JSON `download` = signed `d0.cldisk.com/download/<oid>?at_=<ts>` URL; download immediately with the Referer header — stale signed URLs 403 within minutes.
- **packWork personIds format**: 9-digit school student IDs do NOT work — the export completes but contains only a placeholder zip (`该考试学生暂未上传附件.txt`). Leave `personIds` empty for whole-class exports; for per-student fetches use the review-page path above.
- **Download-center HTML parsing**: rows are `<ul class="dataBody_td" ...>` blocks with NESTED `<ul>`s — a non-greedy `.*?</ul>` regex truncates before the href; split on block-start positions instead. `data-status="0"` = exporting, `"1"` = ready. Person-filtered exports (按人导出) live under `.../moreuser/<hash>zip/<clazzid>_more.zip` with no workid in the path — resolve them via the URL-decoded `fn=` query param or the `nameText` title.

### jQuery AJAX in browser-harness (Promise pattern)

When you need to make AJAX calls from within the browser context and wait for the result:

```python
result = js("""
new Promise((resolve) => {
    $.ajax({
        url: '/some/api',
        type: 'get',
        data: { key: 'value' },
        success: function(data) { resolve(JSON.stringify(data)); },
        error: function(xhr, status, err) { resolve('ERROR: ' + xhr.status); }
    });
});
""")
```

Note: `js()` with `await_promise=True` handles this automatically in browser-harness. The outer `new Promise` wrapper is needed because `$.ajax` doesn't return a native Promise.

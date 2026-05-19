# Step 02: Course, Class, Assignment

Read `references/agent-rules.md` first. This step is read-only discovery.

## Course Selection

Prefer the read-only discovery script before browser/DOM exploration:

```bash
python scripts/chaoxing_discover.py \
  --cookie-file cx_cookies.txt \
  --course "人工智能原理" \
  --class-contains "闵"
```

Use JSON when another tool or agent will consume the result:

```bash
python scripts/chaoxing_discover.py \
  --cookie-file cx_cookies.txt \
  --course "人工智能原理" \
  --class-contains "闵" \
  --json
```

If the teacher has multiple courses and only the class hint is known, omit `--course`; the script scans all teacher courses and returns only courses with matching classes:

```bash
python scripts/chaoxing_discover.py \
  --cookie-file cx_cookies.txt \
  --class-contains "闵"
```

If neither `--course` nor `--class-contains` is provided and multiple courses exist, the script lists the course choices instead of stopping with an ambiguous-course error.

The script reports course id, `cpi`, base `clazzid`, matching class ids, assignment titles, `workId`, submitted count, pending-review count, unsubmitted count, and review-list URL. It does not open student submissions or download/export work.

Use the manual DOM route below only when the script fails, the page structure changes, or the teacher needs a page-specific detail not emitted by the script.

Open the course list and identify available teacher courses. If the target course was not specified, present the course names and ask the teacher to choose.

Common entry points:

- personal space: `https://i.chaoxing.com`
- course list iframe: `/visit/interaction?...`
- teacher course page: `/mooc2-ans/mycourse/tch?courseid=...&clazzid=...&cpi=...`

Extract visible teacher courses from the current page:

```js
Array.from(document.querySelectorAll("a"))
  .filter(a => a.href.includes("courseId") || a.href.includes("courseid"))
  .map(a => ({ text: a.innerText.trim(), href: a.href }))
  .filter(x => x.text.length > 1);
```

If multiple courses match, show the candidate names and ask the teacher to choose.

## Assignment And Class Context

Assignment list URL:

```text
https://mooc2-ans.chaoxing.com/mooc2-ans/work/list?courseid=COURSEID&clazzid=CLAZZID&cpi=CPI
```

Class-filtered URL:

```text
https://mooc2-ans.chaoxing.com/mooc2-ans/work/list?courseid=COURSEID&selectClassid=CLAZZID&cpi=CPI&status=-1&v=0&topicid=0
```

Assignment discovery should be DOM-driven:

```js
var links = Array.from(document.querySelectorAll("a[onclick*='toMarkWork'], a[href*='work/mark']"));
links = links.map(a => {
  var row = a.closest("tr") || a.closest("li") || a.closest(".workList") || a.closest("div") || a.parentElement;
  var data = a.getAttribute("data") || a.href || "";
  var text = row ? row.innerText.trim() : a.innerText.trim();
  var workId = (data.match(/workId=(\d+)/) || data.match(/workid=(\d+)/) || [])[1] || "";
  return { text, data, href: a.href, workId };
}).filter(x => x.text || x.data || x.href);
```

If the target assignment is not named, list visible assignment titles/counts and ask the teacher to choose.

## Review List

Student rows usually expose `workAnswerId` through review links:

```js
Array.from(document.querySelectorAll('a[onclick*="toMarkWork"]')).map(a => {
  var row = a.closest("li") || a.closest("tr") || a.closest("div") || a.parentElement;
  var data = a.getAttribute("data") || "";
  var workAnswerId = (data.match(/workAnswerId=(\d+)/) || [])[1] || "";
  return { data, workAnswerId, rowText: row ? row.innerText.trim() : a.innerText.trim() };
});
```

Before scoring, record and show:

- course name and `courseid`
- visible class name and `clazzid`
- assignment title and `workId`
- submitted / pending / missing counts

Chaoxing may show an all-class assignment card, then switch to a specific class on the review list. Re-check the visible class name and counts after entering the review list.

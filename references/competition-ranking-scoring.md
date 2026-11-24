# Competition-Ranking-Based Assignment Scoring

When the teacher asks to grade an assignment (typically 实验五 神经网络) based on MNIST competition rankings, use this workflow instead of the normal concise/detailed scoring.

## When to Use

- The teacher says "根据排名打分" or "按比赛结果批改"
- The assignment is tied to a 课堂模王赛 MNIST competition
- The competition has ended and final rankings are available

## Workflow

### 1. Get Competition Rankings

Query the SQLite DB (container may be stopped):

```bash
DB=/var/lib/docker/volumes/minist_compact_mnist-runtime/_data/app.db
COMP_ID="<competition_id>"

sudo sqlite3 -header -column "$DB" "
SELECT t.name as 队名, MAX(r.accuracy) as 最高准确率,
       MAX(r.param_count) as 参数量, COUNT(r.id) as 提交次数
FROM teams t
LEFT JOIN submission_results r ON r.team_id = t.id AND r.competition_id = '$COMP_ID'
WHERE t.competition_id = '$COMP_ID'
GROUP BY t.id
ORDER BY 最高准确率 DESC NULLS LAST;
"
```

Get team members:

```bash
sudo sqlite3 -header -column "$DB" "
SELECT t.name as 队名, GROUP_CONCAT(u.username, '、') as 队员
FROM teams t
JOIN users u ON u.team_id = t.id AND u.competition_id = t.competition_id
WHERE t.competition_id = '$COMP_ID'
GROUP BY t.id
ORDER BY t.name;
"
```

Filter out "测试队伍" (admin test team) — it has no real submissions.

### 2. Map Members to Chaoxing Student IDs

Build a name→student_id map from the class's downloaded materials CSV (e.g. `grading_metrics.csv`).

**Pitfall**: Some students may appear in the Chaoxing mark-list but NOT in the downloaded materials (e.g. 罗有东 was registered under a different name or joined the class late). To find them, query the mark-list API directly:

**Pitfall: mark-list pagination.** The `prePageSize`/`prePageNum` parameters alone do NOT advance pages — all pages return the same first 20 students. You must include `pages` and `size` parameters (matching the review-work URL format) for pagination to work. The server ignores `prePageSize` values above 20 and always returns 20 per page. Check `totalPage` in the HTML to know how many pages to fetch.

```python
# Fetch mark-list pages and search by name
import http.cookiejar, urllib.request, urllib.parse, re
from html import unescape

cj = http.cookiejar.MozillaCookieJar('cx_cookies.txt')
cj.load(ignore_discard=True, ignore_expires=True)
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def fetch_mark_list(page, work_id, clazzid):
    data = {
        'courseid': '204565237', 'clazzid': clazzid, 'cpi': '492206399',
        'workid': work_id, 'submit': 'true', 'evaluation': '0', 'unEval': 'false',
        'state': '0', 'groupId': '0', 'from': '', 'ceyan': '0', 'chapterid': '0',
        'workLibraryid': '', 'prePageSize': '20', 'prePageNum': str(page),
        'noBack': 'false', 'topicid': '0', 'backurl': '', 'attachmentWorkId': '',
        'sort': '0', 'order': '0', 'status': '0',
        # CRITICAL: these two parameters control actual pagination
        'pages': str(page), 'size': '20',
    }
    url = 'https://mooc2-ans.chaoxing.com/mooc2-ans/work/mark-list?' + urllib.parse.urlencode(data)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'X-Requested-With': 'XMLHttpRequest'})
    with opener.open(req, timeout=60) as resp:
        return resp.read().decode('utf-8', errors='replace')

# Parse each page: extract student_id, name, workAnswerId from <ul class="dataBody_td"> blocks
all_students = {}
for page in range(1, 5):
    html = fetch_mark_list(page, work_id, clazzid)
    total_match = re.search(r'totalPage.*?value="(\d+)"', html)
    total_pages = int(total_match.group(1)) if total_match else 1
    for block in re.findall(r'(<ul class="dataBody_td".*?</ul>)', html, re.S):
        wid_match = re.search(r'<ul class="dataBody_td" id="(\d+)"', block)
        name_match = re.search(r'py_name[^>]*>([^<]+)<', block)
        sid_match = re.search(r'>(\d{9})<', block)
        if name_match and sid_match:
            sid = sid_match.group(1)
            if sid not in all_students:  # dedupe across pages
                all_students[sid] = {
                    'name': unescape(name_match.group(1).strip()),
                    'workAnswerId': wid_match.group(1) if wid_match else '',
                }
    if page >= total_pages:
        break
```

### 3. Assign Score Bands by Ranking

The teacher confirmed this band scheme (adjust number of tiers based on team count):

| Rank Tier | Score Range | Example (9 teams) |
|-----------|-------------|-------------------|
| 1st | 95-96 | 1st place |
| 2nd-3rd | 86-90 | 2nd, 3rd |
| 4th-5th | 80-85 | 4th, 5th |
| 6th-7th | 72-78 | 6th, 7th |
| 8th-9th | 65-70 | 8th, 9th |
| Did not participate | 50 | No competition record |

For fewer teams (7 teams in ZK2301), the bands were:

| Rank Tier | Score Range |
|-----------|-------------|
| 1st | 95-96 |
| 2nd-3rd | 86-88 |
| 4th-5th | 70-77 |
| 6th-7th | 64-68 |
| Did not participate | 50 |

Use `random.randint(lo, hi)` with a fixed seed for reproducibility. Each team member gets a random score within their team's band.

### 4. Handle Edge Cases

- **Students who didn't compete**: The teacher's rule is 50 points. Check the competition DB for their username; if absent, assign 50.
- **Students who didn't submit the assignment**: Skip them (no score to write).
- **Students in competition but not in Chaoxing class**: Cannot grade — report to teacher.
- **Students in Chaoxing but not in downloaded materials**: Query mark-list API directly (see step 2 pitfall).
- **Late submissions (补交)**: If students submit after the initial batch, grade them using the same ranking-based scheme. Use `session_search` to find the previous scoring scheme if you don't remember it.

### 5. Submit Scores

Use the standard `submit_scores.py --method list-input` workflow. For partially-graded assignments (some students already graded), create a CSV with only the pending students to avoid overwriting existing scores.

## Competition ID Reference

Known competition IDs (query `competitions` table to verify):

| Name | ID | Class |
|------|----|-------|
| 课堂模王赛-ZK2301 | d5222ee2-f72a-4222-a426-79f2a47f90d5 | 智能科技2301-闵 |
| 课堂模王赛-ZK2302 | 12b24067-6e5e-4d26-bfb7-2b2418a80178 | 智能科技2302-闵 |
| 课堂模王赛-WLW2303 | 2d6842a0-3de7-443d-b386-782c47ea98f5 | 物联网2303-闵 |
| 课堂模王赛-XG2502 | d71ea8f1-2fa5-4b7f-867c-d69562ba309b | 信工(专升本)2502-闵 |

Always verify with `SELECT id, name FROM competitions` before using, as new competitions may have been created.

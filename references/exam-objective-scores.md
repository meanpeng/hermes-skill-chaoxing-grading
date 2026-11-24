# Extracting Exam Objective Scores from Markpaper

The Word answer record export (`download_exam_zips.py --format word`) does NOT include auto-graded objective scores. All `exported_score` fields will be `0`. The actual scores live in the Chaoxing markpaper page — which is **server-rendered HTML**, fetchable with a plain authenticated GET (no browser needed).

## Why This Matters

For exams with mixed objective + subjective questions:
- Objective questions (单选/多选/判断/填空) are auto-graded by Chaoxing
- Subjective questions (简答/论述/计算) need manual review
- The Word export only shows the student's answers, not their auto-graded scores
- To compute the final total, extract objective scores from markpaper and add reviewed subjective scores

## Step 1 — Mark-list rows (raw API)

```
POST https://mooc2-ans.chaoxing.com/mooc2-ans/exam/test/markresult-new
```

Required headers:
```
X-Requested-With: XMLHttpRequest
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
Referer: https://mooc2-ans.chaoxing.com/mooc2-ans/exam/test/marklist?clazzid=CLAZZID&courseid=COURSEID&cpi=CPI&id=RELATIONID
```

POST parameters:
```
courseid=COURSEID
clazzid=CLAZZID
cpi=CPI
ut=
id=RELATIONID
sw=
schoolId=-1
schoolName=
sort=
sorttype=
state=1
status=-1
groupIds=
groupid=-1
reviewMarkLabel=0
markType=0
hideInvigilation=0
hideRetest=false
updateScore=1
allowAnnotationRedoDownload=1
pages=1
size=100
```

Response JSON `data` array per entry: `loginName` (学号), `createUserName` (姓名), `id` (answer ID), `answerScore` (0 until graded — never use as the objective score), `mark` (待批阅/已批阅), `markUrl` (path to the markpaper page).

Pitfall: `submit_exam_scores.get_mark_rows()` returns a STRIPPED row dict without `markUrl`. When you need markUrls, POST the raw API yourself and use the raw rows.

## Step 2 — Fetch each markpaper (plain GET)

```
GET https://mooc2-ans.chaoxing.com{markUrl}
```

Returns ~260KB of server-rendered HTML containing the full paper: question stems, options, the student's answers, correct answers/参考要点, and per-question score inputs. Rate-limit to ~1 fetch per 0.3-1s.

## Step 3 — Parse question blocks

Split by question container (question type is in the split head):

```python
parts = re.split(r'<div class="questionWrap"[^>]*index="\d+" name="', html)[1:]
for p in parts:
    qtype = p[:12].split('"')[0]   # 单选题/多选题/判断题/填空题/简答题
```

**Score inputs** — objective questions carry a readonly pre-filled input; subjective (简答) questions have NO `inputBranch` input at all (they are graded in the UI separately):

```python
m = re.search(r'name="score(\d+)"[^>]*class="inputBranch questionScore"[^>]*value="([\d.]*)"', p)
# filled  -> objective, value = auto score
# missing -> subjective, needs rubric/manual scoring
```

Per-question max: `<input id="fullScore\d+" value="20.0" />`. Objective total = sum of filled score values. Question IDs are internal IDs, not sequential — do not assume order.

**Student answers**:
- Choice questions: `学生答案:</i></span><span class="colorDeep"><i class="fontWeight">B</i>`
- 简答/填空: text inside `<div class="stuAnswerWords textWrap">...` (strip tags, collapse whitespace)

**Correct answers / 参考要点**: inside `id="correctanswer_<qid>"` (or `class="disablePosition"`) div, prefix `参考要点：`. Strip tags. The 参考要点 clauses are the grading rubric — split on `；`.

## Step 4 — Grade subjective questions by reference-point coverage

For a rubric like 「摄像头实时显示流程」 with 7 reference clauses, score = `round(20 * matched / 7)` where each clause is a keyword regex (e.g. 打开/VideoCapture, 循环/read, 判断成功/ret, 处理, 显示/imshow, 按键/waitKey, 释放/destroy). For contrast questions (分类 vs 检测), score per contrast point (类别判断 / 位置框 / 多目标), and recognize coordinate arrays like `【100,200,300,400】` as expressing a bounding box even without the word 位置/框.

Rules:
- Empty or <10-char answers score 0; a bare topic restatement scores a minimal partial.
- Answers that are substantively OFF-TOPIC (e.g. describing a network streaming pipeline when the reference is the OpenCV capture loop) score low even if well-written — coverage of the REFERENCE points is the metric.
- Identical-wording answer clusters across students are copy signals; note them for the teacher but score each by coverage.
- Quiz scores are exact (objective + rubric subjective); NO jitter — the ±1-2 jitter rule is for report/content grading, not exams.

## Step 5 — Submit and verify

Build `student_id,score` CSV (score = objective total + rubric subjective), then:

```bash
python3 scripts/submit_exam_scores.py --courseid ... --clazzid ... --cpi ... \
  --relationid <rel> --scores-csv quiz.csv            # dry-run: shows 0.0 -> target per row
python3 scripts/submit_exam_scores.py ... --confirm-submit
```

Verify by re-fetching the raw markresult rows and diffing every student's score against the CSV before reporting success (n/n matched).

## Pitfalls

- The `answerScore` field is always `0` before teacher submission — do NOT use it as the objective score.
- Question IDs are not sequential; match by ID, not position.
- Some rows may lack `markUrl` (special status) — skip them and report.
- Rate-limit markpaper fetches; a 404 on an empty markUrl means you requested an empty path — guard the URL.
- The `sumScore` input on the page starts at 0 until the teacher submits — compute totals from per-question inputs.

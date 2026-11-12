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
- `references/exam-objective-scores.md`: markresult API + markpaper 题块解析 + 客观题分提取 + 简答按参考要点覆盖度自动评分（测验全流程：算分→CSV→提交→核验）。
- `references/fullclass-grading.md`: 整个实验全班批改的有序流程 — 整班包下载、嵌套解包、全班互查、分档出稿、提交核验。
- `references/mnist-competition-grading.md`: grading experiment 5 based on MNIST competition rankings instead of report content.
- `references/guide-copy-check.md`: 指导书抄送检查 recipe — guide+template-discounted net similarity, banding table, own-image audit.
- `references/project-grouping.md`: 综合项目 pull + team-grouping recipe — streaming nested-archive inspection without full extraction, fingerprint/Jaccard grouping, roster extraction, materials-only gate note.
- `references/late-submission-grading.md`: 补交 grading — pending discovery from mark-list rows, per-student attachment download via review-work/ananas (no export queue), reference-corpus evidence with image owner-count classification, recovering the original band scheme from prior grading dirs.

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
- **markpaper 页面是服务端直出的，不要急着上浏览器**：脚本带 cookie GET `markUrl` 返回完整 260KB HTML——题目、选项、学生答案、正确答案/参考要点、每题得分框全在里面（客观题为 readonly 已填分，主观题为空）。只有拿到明显瘦壳（无 `questionWrap`）时才怀疑 cookie/Referer 问题，浏览器是最后手段。解析配方见 `references/exam-objective-scores.md`。
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
- **指导书抄送检查 (实验八 workflow)**: When the teacher supplies the 实验指导书 and allows copying its 原理/步骤/环境 sections, raw pairwise text similarity is inflated by (a) the guide sections everyone copies and (b) the shared report template (~1000+ chars of 成绩统计表/报告头) — band pairs on NET similarity only, never raw. Run `scripts/guide_similarity.py --workdir <dir> --guide <指导书.docx>` instead of hand-rolling difflib cells; full recipe, banding table, and own-image audit in `references/guide-copy-check.md`. Check "0 own images" students separately — borrowed same-byte real screenshots violate the teacher's "图和文字得有自己的" rule even when text is independent.
- **Mark-list HTML 2026-11 改版**: 行元素现在是 `<ul class="dataBody_td mark-time-row" id=.. createid=..>`（class 带后缀），且行内嵌套 UL 会让非贪婪 `.*?</ul>` 提前截断。submit_scores.py 已修复（按起始位置切分）；其它手写解析照抄此法：先 finditer 起始位置再切 chunk。
- **packWork 按人导出 personIds 不认 9 位学号**: 传学号会生成只含"该考试学生暂未上传附件.txt"的占位包；且导出队列可能极慢（25分钟+）。批量下载少量学生的附件，直接走批阅页直链：GET `/mooc2-ans/work/library/review-work?courseid=&clazzid=&workId=&workAnswerId=`（注意路径有 `/library/`），页面里 `objectid="..." filename="..."` 即附件，再 GET `/mooc2-ans/ananas/status/{objectid}`（**必须带 Referer: mooc2-ans**）取 JSON 的 `download` 直链（d0.cldisk.com，token 一次有效，须现取现用 + Referer 头）。全班对比语料仍用整班导出包。
- **pip index broken on this server**: pip.conf points to Tencent internal mirror `mirrors.tencentyun.com` which is unreachable; install with `pip install <pkg> -i https://pypi.org/simple` (e.g. pycryptodome for the login script).
- **测验批阅数据在 markpaper 页里**: `submit_exam_scores.py get_mark_rows` 拿不到 markUrl，需自己 POST MARK_RESULT_URL 取原始行（含 markUrl、id=testUserRelationId）。每生的 markpaper 页是服务端直出的整张卷：学生答案/正确答案/每题得分框（客观题已自动判分 readonly，主观题空待填）。逐生 GET 该页即可解析客观分+简答原文+参考要点（在 objAnswer_right/answerAnalysis div，各测验结构略有差异）。总评 = 客观分 + 简答按要点覆盖度给分。
- **测验简答抄袭判定**: 把清洗后的简答文本按题号两两比对（长度≥15 且相似度≥0.85）分组，命中组按教师指示降分（如简答减半、保底非 0）。AI 传答案常见成簇，跨班同卷也会互传。
- **改分陷阱**: 对已批阅的行改分时，默认列表查询可能不再返回该行导致 no submitted exam row matched；不同班必须用各自的 clazzid+relationid 提交，混在一个 CSV 里会静默丢一半。
- **附件型作业(如综合项目)的附件重下载**: 批阅页 objectid 藏在 insertCloud.html iframe 标签里（objectid/filename/filesize 属性）；这类附件的 status 接口在 **mooc1.chaoxing.com/ananas/status/{oid}**（mooc2-ans 路径会 404），下载带 Referer 即可。整班包删除后可用此法按人补拉。
- **跨班交错提交**: 学生可能从另一个班的作业入口提交（如饶简在2302但综合项目交在2301入口），其 workAnswerId 在另一班 mark-list 里；写分时按行所在班级归组，别按学生所属班硬套。分组归纳名单与实际提交人对不上时，先用 mark-list 逐人核对再定论。
- **Materials-only runs skip the scoring gate**: when the teacher explicitly asks to download/organize submissions with no scoring request (e.g. 拉取下来分组归纳), the explicit request is the scope confirmation — proceed to download/inspect without score-range/mode questions; the gate exists for grading runs, and no grade writes happen either way. See `references/project-grouping.md`.
- **Group team projects by inner-archive fingerprint, not archive md5**: teammates zip the same project tree individually — same sizes, different md5 (zip timestamps). Fingerprint = sorted (name,size) of the project archive's contents; loose-match re-packaged copies (venv included, "reduced", "(2)") by name-set Jaccard ≥0.5; confirm with pptx 组员 lists / paper signature tables. See `references/project-grouping.md`.
- **RAR5: use 7z, not unrar**: `unrar lb -inul` fails silently (0 files, no error) on RAR5 archives; `7z l` lists them. The rar sits nested inside the student zip — stream it to scratch, list, delete.
- **Multi-GB attachment downloads run as background processes**: they exceed the 600s foreground cap and get auto-promoted. Monitor with `ls -la <output-dir>` from a separate call; piping the download command through `tail` hides all progress until exit. Run `df -h` before launching whole-class pack downloads (they run several GB) and delete the pack zips plus extracted late-student attachments once scores are written AND verified — the durable evidence archive is the analysis JSONs + final CSVs, not the binaries.
- **交实验指导书 = 1 分（老师裁定）**: students whose submission is only the guide document / teacher material pack (no own report content anywhere, verified by the nested-zip sweep) get 1 分, not 60 and not 打回 — show them as a separate 无报告 flag row in the draft table.
- **Nested attachment structure**: outer zip → per-student zip (or folder, or bare top-level `学号-姓名.docx`) → project archive. Open nested zips via `zipfile.ZipFile(outer.open(entry))` (ZipExtFile is seekable) instead of full extraction when disk is tight; extract only small docs. Base-name mapping that strips only `.zip` misses bare top-level submissions — strip any extension.
- **补交 grading uses the ORIGINAL bands**: recover score ranges and thresholds from the prior run's `make_draft*.py` + `final_*.csv` in the experiment's grading dir before scoring late submissions — new late grades inherit the old scheme, and a late submission duplicating an already-graded classmate's report puts the LATE student in the 实锤 band without re-opening the earlier score. See `references/late-submission-grading.md`.
- **Fetch specific students via the review page, not packWork**: `/mooc2-ans/work/library/review-work?...` (the `/library/` segment is required) → iframe `objectid`/`filename` → `/ananas/status/<oid>` with a Referer header → signed download URL used immediately. packWork `personIds` filled with 9-digit school IDs yields a placeholder `该考试学生暂未上传附件.txt` zip and the export queue can stall for tens of minutes.
- **Mark-list rows need prefix matching**: row containers carry suffix classes (`<ul class="dataBody_td mark-time-row" id=.. createid=..>`) and the current score lives in `class="inp80 scoreInput"` — match `dataBody_td[^"]*"` and read `value=` from the scoreInput, or you silently parse 0 rows.
- **Same-byte image evidence requires owner-count classification**: guide/template screenshots appear in nearly every student's package; only images shared by a small cluster (2–7 students) prove copying — count per-image owners before citing image evidence in a plagiarism draft.
- **Exclude teacher-issued re-uploads**: 实验X.zip / labels.txt / 指导书发放包 appear in most students' uploads with identical size/md5 — identical-across-students means teacher material, never the student's report and never image evidence.
- **Whole-class pack extraction must recurse into nested archives with a large ARCHIVE-size cap**: the outer pack → student zip → project zip chain buries reports 2-3 levels deep, and a member-size cap meant for extracted files (30-60MB) silently skips inner zips larger than the cap — the report inside a 78MB code zip never surfaces. Open nested `.zip` members recursively (depth ≤3, archive cap ~200MB); apply the small-file cap only to files you WRITE. Verify coverage by listing student dirs still lacking a `.docx` (not by file counts) and keep extracting until that list holds only genuinely report-less students; rar-only students need the rar streamed out and `unrar x` (list RAR5 with 7z per the pitfall above).
- **Detect the template-hub floor before banding mid-similarity pairs**: if many students' TOP pairwise similarity converges on one tiny (~1-1.5k char) report, that doc is the shared template skeleton, and its hit band (~60-70%) is the class's template floor — hub hits are not copying. Band only mutual pairs ABOVE the floor between docs that each carry own content (e.g. a 70.9% mutual pair where neither side's top sim is the hub = real copying; a 66% hit on the hub = template, 不罚).
- **No-precedent experiment uses the standing band ladder**: 实锤 (同字节实拍图+高字似) 65-68; ≥97% text-only 72; net-sim 73-90 → 77; 58-73 mutual-real → 79-81; same-byte images + template-floor text → 88; normal base 95 (≥5000字 or ≥8图) / 94 (≥3000) / 91 (<1700) / else 93, jitter ±1 floor 90. Still recover per-experiment overrides from prior `make_draft*.py` first — the ladder only fills gaps for experiments never graded before.
- **Code-only submissions without a report get 60 + a separate flag row** (teacher decides 打回 or accept) — distinct from 交指导书 = 1 分; do not auto-apply the 1-分 ruling to students who submitted real work but no report docx.


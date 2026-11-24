# Late-Submission (补交) Grading

Grading students whose submissions arrived after a batch was already scored. Governing rule: the score range, band scheme, and requirements are the ORIGINAL run's — recover them first and do not invent new bands.

## 1. Recover the original scheme

The experiment's prior grading directory is the authoritative record (server convention: `~/grading_exp1`, `~/grading_exp2`, `~/expN_grading`):

- `make_draft*.py` — the exact band rules: 实锤/字似/轻度 thresholds, normal-band bases (text length / image count), jitter seed, any teacher-ruled BUMP. Copy these numbers verbatim into the late draft.
- `final_2301.csv` / `final_2302.csv` — submitted scores; observed ranges prove the bands.
- `marklists.json` — student → workAnswerId map captured at grading time.
- `docs/` / `students/` — leftover reference corpus (some dirs keep it, some only analysis JSONs). Present = free corpus; absent = download a whole-class export (step 3).

## 2. Find pending students

Fetch the mark-list per (clazzid, workId) with BOTH `pages` and `size` params (pagination contract in `competition-ranking-scoring.md`). Parse rows:

- Row container: `<ul class="dataBody_td ...">` — suffix classes like `mark-time-row` are appended, so match `dataBody_td[^"]*"`, never the exact string `dataBody_td"`. An exact-match regex silently parses 0 rows.
- Per row: `id="<workAnswerId>" createid="<personId>"`, name via `py_name`, school ID via `>(\d{9})<`, current score via `class="inp80 scoreInput" ... value="..."`. Empty or `0` = pending.
- `current=0` also covers students who never submitted; the review-page fetch (step 3) reveals them — their page has no student attachments.
- Save `{cls: {exp: {sid: {name, workAnswerId, current}}}}` once; reuse for downloads, drafts, and the submit CSV.

## 3. Download late students' attachments

Do NOT fetch specific students via packWork with `personIds`: school-ID personIds produce a placeholder zip (~226 bytes containing only `该考试学生暂未上传附件.txt`), and the export queue can take 25+ minutes per batch. Use the review page (seconds per student):

1. `GET /mooc2-ans/work/library/review-work?courseid=..&clazzid=..&workId=..&workAnswerId=..&groupId=0&from=&sort=0&order=0&status=0&pages=1&size=20&topicid=0` — the `/library/` segment is required; `/mooc2-ans/work/review-work` without it 404s.
2. Parse attachments from iframe attributes: `objectid="<32-hex>" filename="<name>"` (also appears HTML-escaped as `objectid=&quot;...&quot;`).
3. `GET https://mooc2-ans.chaoxing.com/ananas/status/<objectid>` with header `Referer: https://mooc2-ans.chaoxing.com/<page>` — omitting Referer returns 403. JSON `download` holds a signed `d0.cldisk.com/download/...?at_=<ts>` URL plus `filename`.
4. Download that URL immediately with the Referer header. Signed URLs are short-lived — one fetched minutes earlier 403s. Fresh status call → immediate download always works.

For the whole-class reference corpus, submit `packWork` with `personIds` empty (whole class), then poll `/mooc2-ans/tcm/downloadcenter`:

- Entries are `<ul class="dataBody_td" ...>` blocks containing NESTED `<ul>`s — a non-greedy `.*?</ul>` regex truncates before the href. Split on block-start positions and cut at the next start.
- `data-status="0"` = exporting, `"1"` = ready (href present). Stale entries show 过期 and drop off the list.
- Person-filtered exports (按人导出) have URL `.../moreuser/<hash>zip/<clazzid>_more.zip` with NO workid in the path — resolve via the URL-decoded `fn=` query param (holds the full export title) or the `nameText` title. Full-class exports keep `<clazzid>_<workid>.zip` naming.
- The queue serializes jobs: submit ALL pack requests first, then poll, instead of one at a time.

## 4. Evidence analysis against the reference corpus

Corpus = whole-class export (nested per-student zips; see `project-grouping.md` for streaming inspection) plus any leftover local docs. For each late student:

- Pick the MAIN report: longest extracted docx text, skipping files named `指导*`. If the student only re-uploaded the teacher's material pack there is no report at all — flag for the teacher instead of banding.
- Sweep nested zips before declaring 无报告: list every member of EVERY zip in the submission (including the student's own packed zip), not just top-level files — reports hide inside student zips whose names are CP437-mojibake (macOS packing), and the `.docx` extension still survives the garbling so extension matching finds them. A zip containing only datasets/CSVs/images with zero document files means genuinely no report.
- Detect guide-as-report: if the longest docx's text starts with the 指导书 header (课程名称/制定教师/实验项目名称) and runs through 实验报告要求/思考题 sections, the student submitted the guide document itself, not a report — zero own content. Standing teacher ruling: these are recorded at 1 分 (not the 实锤 band, not 打回) unless the teacher says otherwise; flag them separately in the draft table so the teacher sees the count.
- Text similarity: difflib SequenceMatcher(autojunk=False), matching blocks ≥20 chars, pct = matched / min(len_a, len_b), max across the classmate's docx files. Threshold per that experiment's make_draft rules.
- Same-byte image md5 (docx `word/media/` + standalone images), THEN classify each hit by owner count across the corpus: owners ≈ class size (e.g. 29–34 in a 33-person class) = guide/template screenshot, ignore; owners 1–7 = real copying evidence, cite; owners in between (roughly 8 to half the class) = semi-common, too ambiguous to attribute — do not band on it alone. Record per-image owner lists in the draft.
- docx metadata (dc:creator / cp:lastModifiedBy) overlap with a cluster corroborates; metadata alone is never proof (standing teacher ruling).
- Teacher-material contamination: review pages and exports include teacher-issued files everyone re-uploads (实验X.zip, labels.txt, 指导书发放包). Identical filename+size/md5 across many students = not student work — exclude from report selection AND image evidence.
- 复查只松不紧 applies to already-graded scores only; late submissions are new grades at the original bands. When a late submission duplicates an already-graded classmate's report, the LATE student takes the 实锤 band — the earlier submitter's existing score is not re-opened.

## 5. Draft and write

Draft every late student with the original band numbers ±1–2 jitter, show the teacher a Chinese Markdown table (band, evidence, proposed score), and submit only after explicit confirmation via `scripts/submit_scores.py --method list-input --confirm-submit` with the pending-only CSV (workAnswerIds from the fresh mark-list fetch). Verify by re-fetching the mark-list and diffing every `current` against the CSV.

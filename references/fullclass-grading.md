# Whole-Experiment Class Grading (全班批改)

Ordered procedure for grading an entire experiment for both classes (e.g. 实验九): pull the whole-class packs, build a mutual-plagiarism corpus, band, draft, submit after teacher confirmation, verify. Pitfalls referenced here are detailed in SKILL.md; this file is the order of operations.

## 1. Orient

```bash
python3 scripts/check_cookie.py
python3 scripts/chaoxing_discover.py --course <课程名>
```

Read the workId per class, submitted/pending/unsubmitted counts. Confirm scoring intent with the teacher before downloading anything (scoring-setup gate), unless the teacher's message already states the task and bands.

## 2. Disk check, then download packs

`df -h /` first — whole-class packs run several GB. If free space is short, delete prior runs' pack zips and extracted late-attachment dirs (keep analysis JSONs + final CSVs; they are the durable evidence).

```bash
python3 scripts/download_work_zips.py --course <课程名> --work-id <wid> --format attachment \
  --output-dir <dir> --poll-interval 20 --timeout 1500 --confirm-download
```

Run both classes sequentially in one background process. The pack queue takes 10-25 min; poll with `ls -la <output-dir>/*.zip`. The outer pack contains one zip per student (`<学号>-<姓名>.zip`).

## 3. Extract with nested-archive recursion

Outer pack → student zip → inner project zip → report. Recursion rules (see SKILL.md pitfall "Whole-class pack extraction"): recurse into `.zip` members with a ~200MB archive cap (never the extracted-file cap — that silently skips reports inside big code zips), write only small KEEP files (docx/pdf/images/py/csv/txt/md/json ≤30MB), skip video extensions, stream rar-only students out and `unrar x` (list RAR5 with 7z).

Target layout: `corpus/<class>/<学号>_<姓名>/`. **Verify coverage by listing student dirs that still lack a `.docx`** — not by file counts — and keep extracting until that list holds only genuinely report-less students.

## 4. Mutual-plagiarism analysis

Per student collect: main report text (docx `word/document.xml`, excluding 指导书/发放/模板 filenames), docx creator/lastModifiedBy set, and md5 of every embedded image. Then pairwise per class:

- **Text**: difflib matching blocks (size ≥20) summed over `min(len_a, len_b)` → net similarity %.
- **Images**: same-byte md5 intersection, and per-image owner counts across the class.
- **Metadata**: creator/editor intersections as supporting (never primary) evidence.

Save per-class `analysis_<class>.json` with per-student: text length, image count, dup-image owners, top sims. Results feed every later step and the evidence archive.

## 5. Band

- First recover the experiment's own bands from prior `make_draft*.py` / `final_*.csv`. For experiments never graded before, use the standing ladder (SKILL.md pitfall "No-precedent experiment").
- Detect the template-hub floor before banding mid-similarity pairs (SKILL.md pitfall "template-hub floor").
- Image evidence only from small owner clusters; class-wide images are guide screenshots.
- Teacher rulings to apply verbatim: 交指导书 = 1 分; code-only-no-report = 60 + separate flag row; metadata-only match = not plagiarism.
- Normal band: base by length/image count, jitter ±1 (fixed seed), floor 90. Quiz/exam scores are exact, no jitter.

## 6. Draft → confirm → submit → verify

Draft table in concise Chinese Markdown grouped by band, flag rows first. Wait for the teacher's explicit write confirmation in the current turn. Then:

- Fetch fresh workAnswerIds per class from that class's mark-list (never reuse across classes).
- Write `final/<class>_<experiment>.csv` (`student_id,score,workAnswerId`) containing ONLY the students being graded.
- Dry-run `scripts/submit_scores.py --method list-input` (confirm every target is current=0), then `--confirm-submit`.
- Re-fetch the mark-lists and diff every student's current score against the draft; report n/n matched before calling it done.

Finally delete the pack zips (and any scratch extraction) — disk hygiene the teacher checks on.

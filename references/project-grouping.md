# Team-Project Grouping (综合项目拉取与分组归纳)

Recipe for teacher requests like "拉取最新作业, 分组归纳项目": pull a (usually team-based) comprehensive-project assignment and organize submissions by project/team. No scoring involved.

**Gate note**: when the teacher explicitly asks for a materials pull/organization with no scoring request, the explicit request IS the scope confirmation — do not ask for score range or scoring mode; those gates apply to grading runs. Still never write grades in such runs.

## 1. Discover — all classes, not one

`python3 scripts/chaoxing_discover.py --course <关键词> --json`

- One course commonly has MULTIPLE classes (e.g. 2301/2302), each with its OWN workId for the same assignment title. Collect every class's workId.
- The latest assignment is the one with submitted>0 and pending_review≈submitted near the top of the list.

## 2. Download attachment packages

Dry-run first, then confirm:

```bash
python3 scripts/download_work_zips.py --course <kw> --assignment-contains <kw> \
  --format attachment --output-dir <dir>            # dry run: verify targets
# add --confirm-download --timeout 420
```

- Project assignments are BIG (code + demo video + datasets; multi-GB per class is normal). Check `df -h` before planning extraction.
- The download exceeds the 600s foreground cap and is auto-promoted to a tracked background process. Pipe-free monitoring: `ls -la <output-dir>` in a separate call to watch zip growth — piping the command through `tail` hides all progress until exit.
- `scripts/extract_work_zip.py` fully extracts — do NOT use it on multi-GB packages with single-digit-GB free disk. Stream-inspect instead (step 3).

## 3. Inspect without extracting (streaming nested zips)

Chaoxing attachment zip structure is nested: outer zip → per-student entry → student's archive → project archive. A student entry is one of:
- a zip wrapping everything: `学号-姓名.zip`
- loose files under a folder: `学号-姓名/report.docx`, `.../main.py`
- a top-level bare file: `学号-姓名.docx` (single-doc submissions)

`ZipExtFile` from `outer.open(...)` is seekable, so nested zips open and list for free:

```python
outer = zipfile.ZipFile(big_zip)
with outer.open('233080472-倪玮竟.zip') as st:
    nz = zipfile.ZipFile(st)          # lists without writing anything to disk
    for m in nz.infolist(): ...
```

Walk the levels, record name/size/ext per member, and extract ONLY small documents (DOC_EXT = docx/pdf/md/txt/py/ipynb/pptx/html/csv, ≤30MB each) into `docs/<class>/<student>/`. Skip videos/archives/datasets — record their names and sizes only. This keeps a 5.4GB pull at ~100MB extracted.

## 4. Group students into teams

Signals in order of strength:

1. **Inner-archive fingerprint** — the project archive's contents as a sorted set of `(name, size)` tuples. Identical fingerprint = same team. Teammates' project zips named `gesture_project_N` also carry the group number; the same N across classes is the same project spec.
2. **Loose name-set match** — re-packaged copies of one project (one teammate included `.venv`, someone zipped a `reduced` tree, `(2)` duplicate copies) fail exact fingerprints. Compare name-set Jaccard; ≥0.5 with matching top-level structure = same team. Report what differs.
3. **Codebase identity by distinctive modules** — when packaging differs, matching distinctive module name sets (e.g. `board_view`/`game_logic`/`motion_recognizer` pyc names = whack-a-mole family) prove shared code even across different zip wrappers.
4. **Document rosters** — read the extracted docs: 答辩 pptx 组员 lists and course-paper signature tables (`姓名学号` rows) are authoritative team rosters; a paper signed by 7 names settles a 7-person team. Use rosters to confirm fingerprint groups and to catch members who did NOT submit.

Anti-signals:
- **md5 of student archives is NOT a grouping signal.** Teammates zip the same project tree individually — identical sizes, different md5 (zip timestamps differ). Same-size+same-name is a hint to fingerprint, never the proof.
- Identical full-name-sets across different projects can happen (template reports) — always pair a name match with a code/pptx-title check.

RAR handling: `unrar lb -inul` fails SILENTLY on RAR5 (returns 0 files, exit 0-ish). Use `7z l` (parse `....A` rows for file entries; names contain spaces so split carefully). rar members sit INSIDE the student zip — stream the rar out to scratch, list, then delete.

## 5. Verify coverage, deliver

- Coverage check in code: every student from the mark-list/discovery (per class, submitted count) is assigned to exactly one group. Fix class-label mismatches (a student's class comes from the outer zip they appear in, not from their ID range or your assumption).
- Deliverable: Chinese markdown table `项目组 | 人数 | 成员(班-姓名-学号) | 分组证据`, attach via MEDIA. Evidence column names the signal (PPT roster / fingerprint / paper signature).
- Flag: roster names absent from BOTH class rosters (dropped students), and submitters whose papers carry a teammate's student ID (copy-paste typos — note, don't 'fix').
- Save the grouped markdown next to the download dir so grading sessions can reuse it.

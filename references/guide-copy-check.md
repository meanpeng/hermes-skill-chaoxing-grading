# Guide-Copy Check (指导书查重) for Report Grading

Use when the course posts an 实验指导书 and the teacher wants to catch reports that are mostly guide content, while allowing legitimate copying of the sections he allows (typically 原理/操作步骤/环境). Run AFTER `extract_all.py` + `parse_docs.py` have produced `docs/` and `manifest.json` in the experiment workspace.

## Teacher ruling to confirm before drafting

Confirm two things, not one:
1. Which guide sections MAY be copied without penalty (e.g. 原理/步骤/环境 — usually also 目的 since everyone pastes it into the template field).
2. The ownership rule for the rest: the report must not be entirely guide content — the student needs own text AND own images.

## Procedure

1. **Guide text**: the teacher usually sends the guide docx in chat; it lands under `~/.hermes/cache/documents/`. Extract normalized text (read `word/document.xml`, join `<w:t>` per paragraph, strip ALL whitespace into one string). Save as `<workdir>/guide_text.txt`. Locate the section marker offsets (一、实验目的 / 二、实验原理 / 三、… / 四、… / 五、… / 六、…) so every matched block can be attributed to a section — allowed vs beyond-allowed sections drive the penalty, not the raw total.

2. **Run the evidence script** instead of hand-rolling difflib cells:
   ```bash
   python scripts/guide_similarity.py --workdir ~/expN_grading --guide /path/to/实验指导书.docx
   ```
   It writes `own_analysis.json` (per-student `guide_matched`, `template_len`, `net_own`, `own_img`, `shared_img`) and `net_text_sim.json` (pairs above threshold), and prints top pairs plus students with 0 own experiment images.

3. **Read the numbers in this order**:
   - `guide_cov` / per-section split: is the report mostly guide? which sections beyond the allowed set?
   - `net_own`: chars that are neither guide nor shared template — the student's real writing.
   - `own_img == 0`: every experiment screenshot is borrowed (school crest excluded) — violates the own-image rule even when text is independent.
   - net pairs ≥ 48%: candidate copying clusters.

4. **Vision-classify every shared image group** before using it as evidence: build one labeled contact sheet (per-group thumbnails, members in the label) and classify in a single vision call. Crest/tutorial/boilerplate images = excluded; identical real experiment screenshots (camera frames, OpenCV windows, terminal output, event CSV) = hard evidence. Do not skip this — same-byte files are only meaningful if they are experiment output.

5. **Band on NET similarity, never raw**: see table below. Quote raw similarity only as supporting evidence.

## Why the discount exists

Raw pairwise similarity is inflated by two things every report shares: the guide sections everyone pastes (per teacher ruling, not plagiarism) and the report template (成绩统计表 + 报告头 + checkbox line ≈ 1000+ chars, regex-matched). Two students who each independently copied the same guide sections score 99% raw with net ≈ 0 — punishing them as copiers is a false alarm. Genuine whole-report copying (own analysis prose copied verbatim) survives the discount at ≥90% net.

## Banding table (guide-bearing experiments)

| evidence | band/score |
|---|---|
| net ≥ 90% (or raw ≥ 97%) ± shared same-byte screenshots | 实锤 65-68 |
| report ≥ ~70% guide incl. beyond-allowed sections + 0 own images + <400 own chars | 实锤 66-69 |
| net 73-90% | 76-78 |
| net 58-73% | 79-82 |
| net 48-58% (circulating-source web members) | 83-86 |
| same-byte real screenshots only, text independent | 88-89 |
| guide-heavy but HAS own images AND own analysis | 89-90 |
| normal | 90-96 ±1 (fixed seed) |

The exact numbers are the teacher's call per run — show the draft table and let him adjust before writing.

## Pitfalls

- A hub student sharing ~800 net chars with 8+ classmates is ONE circulating source document — band the web members once at the same level instead of creating a per-pair band; only pairs well above the web baseline (e.g. a 96% net pair inside the web) get the heavier band.
- Compare lengths with `min(len_a, len_b)` and subtract `min(ban_a, ban_b)`; subtracting the average over-punishes the shorter original and under-punishes the longer copy.
- Filename checks alone are not enough: nobody names their file 实验指导书.docx — the copy shows up as guide text inside an ordinarily-named report.
- Crest/template image hashes: auto-detect as any image hash present in ≥50% of reports; do not hardcode per-course hashes.

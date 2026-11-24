# Assignment Scoring Methodology

This reference turns `batch_grade.py` output into a consistent first-pass score suggestion. It is intentionally conservative: the model must still read or inspect the submission evidence before treating the result as final.

Before any scoring work, the teacher must confirm:

```text
score_range: <min>-<max>
scoring_mode: random | concise | detailed
```

Do not download or inspect assignment files until the scoring mode is confirmed. If the mode is `random`, do not download or inspect assignment files at all.

## Modes

- `random`: generate scores randomly inside the confirmed score range. This mode is teacher-directed and does not use assignment evidence. The evidence field must say `teacher-selected random scoring; assignment not inspected`.
- `concise`: use `batch_grade.py` material and metrics output as rough evidence. Inspect only flagged or ambiguous cases.
- `detailed`: open each student's report/attachment and score from actual observed content.

## Inputs

Expected fields from `grading_materials.csv` or `grading_metrics.csv`:

- `status`
- `char_count`
- `img_count`
- `section_signal`
- `key_requirement_signal`
- `preview`
- `report_path`

## Suggested Bands

```text
90-100: complete submission, correct assignment, clear process/results, screenshots or code/output evidence, and the assignment's key requirements are covered
80-89: mostly complete, minor omissions in analysis, screenshots, or conclusion
70-79: submitted and task-relevant, but important evidence or explanation is missing
60-69: minimal completion, weak report, incomplete evidence, or hard-to-verify result
0-59: empty, irrelevant, missing, unreadable, or confirmed serious issue
```

For routine homework, submitted and task-relevant work should usually stay at 70 or above unless the evidence shows a major defect.

## First-Pass Formula

Use this only for `concise` mode to sort and calibrate submissions:

```python
def suggest_score(row, posture="lenient"):
    status = row.get("status")
    chars = int(row.get("char_count") or 0)
    images = int(row.get("img_count") or 0)
    sections = int(row.get("section_signal") or 0)
    key_requirement = str(row.get("key_requirement_signal", "")).lower() in {"true", "yes", "1"}

    if status == "missing_report":
        return 55, "manual_review"
    if status == "unreadable":
        return 60, "auto_confirm_unreadable"

    score = 70

    score += min(10, sections * 2)
    score += min(8, chars // 250)
    score += min(10, images * 2)
    if key_requirement:
        score += 6

    if status == "too_short" and images == 0:
        score = min(score, 72)
    if status == "too_short" and images > 0:
        score = max(score, 78)

    if posture == "strict":
        score -= 5
    elif posture == "lenient":
        score += 3

    return max(0, min(100, round(score))), "draft_only"
```

Clamp the returned score to the teacher-confirmed score range before showing the draft.

## Score Differentiation (Teacher Preference)

In `concise` mode, the first-pass formula often produces identical or near-identical scores for most students (e.g., everyone gets 95). Teachers find uniform scores unrealistic and will reject them. Always apply differentiation before showing the draft:

1. Compute the base score from the formula above.
2. Apply a random jitter of ±1-2 points (use a fixed random seed for reproducibility).
3. Clamp to the teacher-confirmed score range.
4. If the teacher specifies a floor (e.g., "不低于90"), clamp to that floor.

```python
import random
random.seed(42)  # reproducible

def apply_jitter(base, floor=90, ceiling=100):
    delta = random.choice([-2, -1, -1, 0, 0, 1, 1, 2])
    return max(floor, min(ceiling, base + delta))
```

The jitter distribution is slightly biased toward ±1 to avoid extreme spread. Only apply jitter when the base score is already at or above the floor; never jitter a legitimately low score up to the floor.

## Handling CRC-32 Corrupted DOCX Files

When `python-docx` throws `Bad CRC-32 for file 'word/media/imageN.png'`, the docx is still readable — only an embedded image has a checksum mismatch. Extract text directly from the zip:

```python
import zipfile, re

def read_crc_damaged_docx(path):
    """Read text from a docx that fails python-docx due to image CRC errors."""
    with zipfile.ZipFile(path) as z:
        with z.open('word/document.xml') as f:
            content = f.read().decode('utf-8', errors='replace')
            texts = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', content)
            full = ''.join(texts)
            # Count images by listing media entries
            img_count = sum(1 for n in z.namelist() if 'word/media/' in n)
            return full, img_count
```

After extraction, score the student using the recovered `char_count` and `img_count` instead of leaving them at the `unreadable` default. This counts as the agent-side direct inspection required by the rules before escalating to teacher review.

## Finding Pending Students in Partially-Graded Assignments

When an assignment has `pending_review < submitted` (some but not all students need grading), use a dry-run with a dummy CSV containing all students at a placeholder score to discover which students have `current=0` (ungraded). Then create a scores CSV with only those pending students and submit.

```python
# 1. Create dummy CSV with all students at score=95
# 2. Run submit_scores.py --method list-input (dry-run)
# 3. Filter output for rows where current=0
# 4. Create CSV with only those students' actual scores
# 5. Submit only that CSV
```

This avoids overwriting existing grades for already-graded students.

## Essay Scoring Tier System (Teacher-Confirmed)

For essay-type assignments (一课一文 etc.) with multi-dimensional requirements, the teacher's explicit preference is that **dimension coverage is the primary scoring factor**, not word count. A student who writes 7000+ words but only covers 4/8 dimension keywords should score LOWER than a student who writes 3000 words but covers 8/8.

### Dimension Keywords

For the standard "一课一文" assignment analyzing AI technology, check these 8 keywords:

```python
dim_keywords = ['技术背景', '发展现状', '前沿成果', '未来方向',
                '发展趋势', '起源', '核心原理', '发展脉络']
dim_count = sum(1 for kw in dim_keywords if kw in text)
```

### Tier System (80-100 range)

```text
8/8 dims + 3000+ chars + 1000+ personal thinking → 93-100
7/8 dims → 90-93
6/8 dims → 86-90
5/8 dims → 85-86
3-4/8 dims → 83-85 (even if 7000+ words, cap here)
0-2/8 dims → 80-82
```

### Personal Thinking Adjustment

The assignment requires ≥500 chars of personal/critical thinking. Check with:

```python
personal_keywords = ['批判', '个人理解', '个人思考', '使用体验',
                     '我认为', '反思', '体会', '我的看法']
has_personal = any(kw in text for kw in personal_keywords)
# Estimate personal section length from first keyword match to end
```

- Missing entirely: −7 to −8 points
- Below 500 chars: −4 to −5 points
- 2000+ chars: +2 points (strong personal thinking)

### Key Rules

1. **Word count is a secondary modifier** (±1-3 points), never the primary factor.
2. **Scores must have visible spread** — not clustered at one value. The teacher rejected a draft where everyone got 92-98 with 7 students at 100.
3. **100 is acceptable** for truly excellent work (8/8 dims + 4000+ chars + 2000+ personal + structure).
4. **Long essays with poor dimension coverage get capped** — a 12716-word essay with only 4/8 dims gets 85, not 95.
5. **Missing personal thinking is a heavy penalty** — even with 7/8 dims, a student with no personal thinking scores 82, not 90.

## Mandatory Overrides

- Every score must stay inside the teacher-confirmed score range.
- In `random` mode, do not invent content-based evidence, penalties, or quality claims.
- Low text with unique screenshots is not automatically low quality.
- Blank process/result text can be acceptable when screenshots show the work.
- Do not penalize a missing reflection/summary section unless the assignment explicitly requires it. Use `key_requirement_signal` only as a rough positive signal that key assignment requirements may be covered.
- Identical or near-identical submissions need group comparison, not isolated scoring.
- `unreadable` means agent-side direct file inspection is required before teacher-facing review: open alternate report candidates, nested archives/attachments, and available PDF/original-attachment packages with appropriate local tools. Rerunning the material-prep script is not enough. Keep it out of the final manual-review list until direct inspection attempts fail.
- Any score below 70 for a submitted report needs a written defect in `penalty_reason`.
- Any score of 100 needs concrete evidence of completeness in `evidence`.

## Output Schema

Teacher-facing drafts should use this Chinese Markdown table:

```text
| 学号 | 姓名 | 分数 | 档位 | 建议复核 | 说明 |
|---|---|---:|---|---|---|
```

The `说明` column should summarize evidence in plain Chinese. Do not paste raw metric strings in the main draft unless the teacher asks for source/audit data.

Use this CSV schema for scripts or saved artifacts:

```csv
student_id,student_name,score,band,evidence,penalty_reason,needs_manual_review,workAnswerId
```

Keep `needs_manual_review=true` until uncertain evidence has been inspected. For `unreadable`, the inspecting party is the agent first; escalate to teacher review only after direct local file inspection fails.

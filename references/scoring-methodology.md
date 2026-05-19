# Experiment Report Scoring Methodology

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
- `reflection_signal`
- `preview`
- `report_path`

## Suggested Bands

```text
90-100: complete report, correct assignment, clear process/results, screenshots or code/output evidence, meaningful reflection
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
    reflection = str(row.get("reflection_signal", "")).lower() in {"true", "yes", "1"}

    if status == "missing_report":
        return 55, "manual_review"
    if status == "unreadable":
        return 60, "manual_review"

    score = 70

    score += min(10, sections * 2)
    score += min(8, chars // 250)
    score += min(10, images * 2)
    if reflection:
        score += 8
    elif chars >= 300 or images >= 2:
        score -= 4

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

## Mandatory Overrides

- Every score must stay inside the teacher-confirmed score range.
- In `random` mode, do not invent content-based evidence, penalties, or quality claims.
- Low text with unique screenshots is not automatically low quality.
- Blank process/result text can be acceptable when screenshots show the work.
- Missing or weak reflection is a meaningful penalty even if screenshots exist.
- Identical or near-identical submissions need group comparison, not isolated scoring.
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

Keep `needs_manual_review=true` until the uncertain evidence has been inspected.

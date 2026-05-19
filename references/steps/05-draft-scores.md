# Step 05: Draft Scores

Read `references/agent-rules.md` first. Scores must stay inside the teacher-confirmed score range.

## Random Mode

Do not inspect assignment files. Generate random scores within the confirmed range from the student list/IDs only.

Use this evidence string:

```text
teacher-selected random scoring; assignment not inspected
```

Do not invent content-based evidence, penalties, or quality claims.

## Concise Mode

Use `batch_grade.py` material and metrics output as rough evidence. Inspect flagged or ambiguous cases only.

Useful calibration table:

```text
student_id | student_name | chars | images | sections | reflection | status | provisional_band | notes
```

Use `references/scoring-methodology.md` for suggested bands and first-pass formula.

## Detailed Mode

Open every available report/attachment before assigning final draft scores. Evidence must cite actual observed content, not only metrics.

## Score Draft Schema

```csv
student_id,student_name,score,band,evidence,penalty_reason,needs_manual_review,workAnswerId
```

Rules:

- Set `needs_manual_review=true` for unreadable, missing, suspiciously duplicated, image-heavy but not inspected, or mismatched submissions.
- Do not assign below 70 to a submitted experiment report unless `penalty_reason` states the major defect.
- Do not assign 100 unless `evidence` states why it is complete enough for full credit.
- Keep similar submissions within a narrow score range unless a concrete difference is documented.
- If the teacher has not accepted the calibration posture in content-based modes, output score suggestions only and do not prepare a write action.

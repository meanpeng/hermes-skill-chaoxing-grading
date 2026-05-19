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

Chinese calibration prompt template:

```text
我先抽取了 <sample_count> 份代表性提交用于校准：

student_id | student_name | chars | images | sections | reflection | status | provisional_band | notes
<rows>

请确认评分口径：
1）宽松作业口径：完成度为主，普通完整作业分数偏高
2）严格考核口径：更重视完整性、反思质量和证据充分性
3）自定义口径：你直接说明扣分重点

确认后我再生成全量分数草稿。
```

## Detailed Mode

Open every available report/attachment before assigning final draft scores. Evidence must cite actual observed content, not only metrics.

## Score Draft Schema

```csv
student_id,student_name,score,band,evidence,penalty_reason,needs_manual_review,workAnswerId
```

Chinese score draft response template:

```text
已生成分数草稿，尚未写入系统。

目标：
课程：<course>
班级：<class>
作业：<assignment>
评分范围：<score_range>
评分模式：<random|concise|detailed>

汇总：
待写入人数：<n>
需要人工复核：<manual_review_count>
未交人数：<unsubmitted_count>

分数草稿：
student_id,student_name,score,band,evidence,penalty_reason,needs_manual_review,workAnswerId
<rows>

请检查分数草稿。如果需要调整，请指出学生或规则；确认无误后，我再进入提交前确认。
```

Rules:

- Set `needs_manual_review=true` for unreadable, missing, suspiciously duplicated, image-heavy but not inspected, or mismatched submissions.
- Do not assign below 70 to a submitted experiment report unless `penalty_reason` states the major defect.
- Do not assign 100 unless `evidence` states why it is complete enough for full credit.
- Keep similar submissions within a narrow score range unless a concrete difference is documented.
- If the teacher has not accepted the calibration posture in content-based modes, output score suggestions only and do not prepare a write action.

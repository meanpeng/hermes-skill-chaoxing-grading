# Step 03: Confirm Score Range And Scoring Mode

Read `references/agent-rules.md` first. This gate happens before opening student submissions, exporting, packaging, downloading, extracting, or parsing assignment files.

Ask the teacher to confirm:

1. Score range, for example `70-100`, `60-95`, or `0-100`.
2. Scoring mode:
   - `1. random`: random scoring inside the confirmed score range. Do not download or inspect assignment files.
   - `2. concise`: rough scoring from metadata such as parsed text length, section signals, reflection signals, image counts, and previews.
   - `3. detailed`: open and inspect every student's assignment file before assigning scores.

Prompt shape:

```text
请先确认评分设置：
1. 分数范围：例如 70-100
2. 评分模式：
   1）随机评分：直接在范围内随机打分，不下载/不查看作业
   2）简洁打分：根据字数、结构、图片数量、摘要预览等大致内容打分
   3）细致打分：逐个打开作业文件仔细检查后打分
```

Do not continue to open, export, download, extract, or parse assignment files until both fields are confirmed.

Mode behavior:

- `random`: collect only student list and identifiers from the review/score list page. Evidence must be `teacher-selected random scoring; assignment not inspected`.
- `concise`: export/download is needed. Use `batch_grade.py` metadata and metrics; inspect flagged cases only.
- `detailed`: export/download is needed. Open every available report/attachment and cite observed content.

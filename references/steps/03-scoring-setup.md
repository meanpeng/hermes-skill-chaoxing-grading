# Step 03: Confirm Score Range And Scoring Mode

Read `references/agent-rules.md` first. This gate happens before opening student submissions, exporting, packaging, downloading, extracting, or parsing assignment files.

Ask the teacher to confirm in Chinese when the current course/class/assignment context is Chinese. Use the template below as the response shape, filling in the known target ledger first.

1. Score range, for example `70-100`, `60-95`, or `0-100`.
2. Scoring mode:
   - `1. random`: random scoring inside the confirmed score range. Do not download or inspect assignment files.
   - `2. concise`: rough scoring from metadata such as parsed text length, section signals, key-requirement signals, image counts, and previews.
   - `3. detailed`: open and inspect every student's assignment file before assigning scores.

Chinese prompt template:

```text
已定位到目标作业：
课程：<course>
班级：<class>
作业：<assignment>
workId：<workId>
状态：已交 <submitted>，待批 <pending_review>，未交 <unsubmitted>

下一步如果需要继续评分，请先确认评分设置。

请确认：
1. 分数范围：例如 70-100、60-95 或 0-100
2. 评分模式：
   1）随机评分：直接在范围内随机打分，不下载/不查看作业
   2）简洁打分：根据字数、结构、图片数量、摘要预览等大致内容打分
   3）细致打分：逐个打开作业文件仔细检查后打分

请直接回复“分数范围 + 评分模式”，例如：70-100，细致打分。
```

If the target ledger is incomplete, keep the same template but replace unknown fields with `待确认` and collect the missing target information before opening or exporting materials.

Do not continue to open, export, download, extract, or parse assignment files until both fields are confirmed.

Mode behavior:

- `random`: collect only student list and identifiers from the review/score list page. Evidence must be `teacher-selected random scoring; assignment not inspected`.
- `concise`: export/download is needed. Use `batch_grade.py` metadata and metrics; inspect flagged cases only.
- `detailed`: export/download is needed. Open every available report/attachment and cite observed content.

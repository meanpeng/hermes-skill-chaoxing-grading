# Text-Based Essay Assignment Grading

For assignments that are text essays (e.g. 一课一文, 调研报告) rather than lab reports with code/screenshots, the scoring methodology differs from the default lab-report-oriented approach in `scoring-methodology.md`.

## When to Use

- Assignment is a written essay, analysis, or survey — not a lab experiment
- Requirements specify minimum word count and thematic dimensions
- Personal reflection / critical thinking is a graded component
- No code, screenshots, or experimental results expected

## Requirements Extraction

Parse the assignment prompt to extract:

1. **Minimum word count** (e.g. 1500字)
2. **Minimum personal/critical thinking word count** (e.g. 500字)
3. **Required dimensions** (e.g. 技术背景, 发展现状, 前沿成果, 未来方向)
4. **Content constraints** (e.g. "avoid simply piling up materials", "combine personal experience")

## Evaluation Metrics

For each student submission, compute:

| Metric | How | Purpose |
|--------|-----|---------|
| `full_len` | Total character count of extracted text | Check minimum word count |
| `personal_chars` | Characters from first personal/critical keyword to end | Check minimum personal thinking count |
| `dim_count` | Count of required dimension keywords found in text | Check dimension coverage |
| `has_structure` | Presence of 一、/二、/1./2. etc. | Organization signal |
| `has_specific_tech` | Domain-specific terms (Transformer, CNN, NLP, etc.) | Technical depth signal |

### Personal Section Detection

Search for the earliest occurrence of any personal-thinking keyword to estimate where the reflection section begins:

```python
personal_keywords = ['批判性思考', '个人理解', '个人思考', '个人见解', '使用体验',
                     '我的理解', '我的思考', '我认为', '个人观点', '反思',
                     '我的看法', '我的感受', '体会', '个人体验']
```

`personal_chars = full_len - personal_start` (0 if no keyword found).

**Pitfall**: Students who write personal thoughts *throughout* the essay (interleaved with technical content) rather than in a separate section will have `personal_chars` nearly equal to `full_len`. This is not a problem — it means they integrated personal reflection well. Students with `personal_chars = 0` genuinely lack any personal/critical thinking language.

## Scoring Bands for Essays

```text
90-98: Meets word count + personal thinking count + covers most dimensions + structured + technical depth
85-89: Meets word count but missing personal/critical thinking section, or personal section < required minimum
80-84: Below word count requirement or major dimensions missing
```

### Score Modifiers

```python
base = 90
if full_len >= 5000: base += 3
elif full_len >= 3000: base += 1
if dim_count >= 7: base += 2
elif dim_count >= 5: base += 1
if has_structure: base += 1
if has_specific_tech: base += 1
# Cap at 98, apply ±1-2 jitter, clamp to [80, 98]
```

### Common Deductions

- **No personal/critical thinking** (`personal_chars = 0`): deduct to 85
- **Personal section below required minimum** (e.g. < 500字): deduct to 87
- **Below minimum word count** (< 1500字): deduct to 82-85 depending on severity
- **Content extraction failure**: 80 (minimum, do not fail the student for file format issues)

## Dimension Keyword List

Common dimension keywords for AI/tech essay assignments:

```python
dimension_keywords = [
    '技术背景', '发展现状', '前沿成果', '未来方向', '发展趋势',
    '起源', '核心原理', '发展脉络', '发展历程', '关键里程碑',
]
```

Count how many are present (out of 8). A score of 0/8 does not necessarily mean the content is bad — the student may use different terminology. Treat it as a weak signal, not a hard penalty.

## Differences from Lab Report Grading

| Aspect | Lab Report | Essay |
|--------|-----------|-------|
| Screenshots/images | Expected, contribute to score | Not expected |
| Code | Expected | Not expected |
| Word count | Less important | Key requirement |
| Personal reflection | Usually optional | Key requirement |
| Dimension coverage | Process/results focus | Thematic dimensions focus |
| img_count signal | Positive (evidence of work) | Neutral (not expected) |

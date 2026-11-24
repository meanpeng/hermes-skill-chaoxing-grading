# MNIST Competition-Based Grading (Experiment 5)

When the assignment is "实验五 神经网络" (or similar MNIST competition experiment), grades are based on the MNIST classroom competition (课堂模王赛) ranking, NOT on report content.

## Competition Data Location

Competition data lives in the Docker volume `minist_compact_mnist-runtime`:

```bash
DB=/var/lib/docker/volumes/minist_compact_mnist-runtime/_data/app.db
```

## Finding the Competition for a Class

Competitions are named `课堂模王赛-ZKXXXX` where XXXX matches the class identifier:

```sql
SELECT id, name, created_at FROM competitions ORDER BY created_at DESC;
```

Class name → competition ID mapping (examples):
- 智能科技2301-闵 → `d5222ee2-f72a-4222-a426-79f2a47f90d5` (ZK2301)
- 智能科技2302-闵 → `12b24067-6e5e-4d26-bfb7-2b2418a80178` (ZK2302)
- 物联网2303-闵 → `2d6842a0-3de7-443d-b386-782c47ea98f5` (WLW2303)
- 信工（专升本）2502-闵 → `d71ea8f1-2fa5-4b7f-867c-d69562ba309b` (XG2502)

Always query by name pattern — IDs change if competitions are recreated.

## Extracting Rankings

```sql
-- Team members
SELECT t.name as team, GROUP_CONCAT(u.username, '、') as members
FROM teams t
JOIN users u ON u.team_id = t.id AND u.competition_id = t.competition_id
WHERE t.competition_id = '<COMP_ID>'
GROUP BY t.id ORDER BY t.name;

-- Rankings by best accuracy
SELECT t.name as team,
       MAX(r.accuracy) as best_accuracy,
       MAX(r.correct_count) as correct,
       MAX(r.sample_count) as total,
       MAX(r.param_count) as params,
       COUNT(r.id) as submissions
FROM teams t
LEFT JOIN submission_results r ON r.team_id = t.id AND r.competition_id = '<COMP_ID>'
WHERE t.competition_id = '<COMP_ID>'
GROUP BY t.id
ORDER BY best_accuracy DESC NULLS LAST;
```

Exclude "测试队伍" (admin test team) from rankings — they have no submissions.

## Score Mapping by Rank

The teacher's established pattern (from ZK2301 grading, June 2026):

| Rank | Score Range | Notes |
|------|-------------|-------|
| 1st  | 95-96       | Top team |
| 2nd-3rd | 86-88    | |
| 4th-5th | 70-77    | |
| 6th-7th | 64-68    | |

For classes with more teams (9 teams in ZK2302), extend the pattern:
- 1st: 95-96
- 2nd-3rd: 88-90
- 4th-5th: 80-85
- 6th-7th: 72-78
- 8th-9th: 65-70

Always confirm the mapping with the teacher before submitting — they may adjust bands per class.

## Mapping Team Members to Student IDs

Team members in the competition DB use `username` (student names), not student IDs. To submit scores via the Chaoxing API, map names to student IDs using the class's mark-list or the grading metrics CSV from a previously downloaded assignment.

## Workflow

1. Query the competition DB for rankings + team members.
2. Confirm score bands with the teacher.
3. Map team members → student IDs (use any assignment's metrics CSV for the same class).
4. Within each team, apply ±1-2 jitter (same as concise mode) so teammates don't all get identical scores.
5. Create a scores CSV and submit via `submit_scores.py --method list-input`.
6. Students who didn't participate (未提交) are skipped — ask the teacher how to handle them.

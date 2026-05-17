#!/usr/bin/env python3
"""
批量提交分数到超星学习通。
用法：修改 scores 字典和 URL 参数后，在 browser-harness 中执行。

前置条件：
- 已登录学习通（cookies 已注入浏览器）
- 已获取所有学生的 workAnswerId（从批改列表页提取）
"""

import json

# ===== 配置区（使用前填写实际值） =====
COURSEID = ""   # 课程ID
CLAZZID = ""    # 班级ID
CPI = ""        # CPI
WORK_ID = ""    # 作业ID

# 学生学号 → 分数（批改完成后填入）
SCORES = {
    # "学号": 分数,
    # "学号": 分数,
}

# 学生学号 → workAnswerId（从批改列表页提取）
WORK_ANSWER_IDS = {
    # "学号": "workAnswerId",
    # "学号": "workAnswerId",
}

# ===== 提交逻辑 =====
BASE_URL = (
    "https://mooc2-ans.chaoxing.com/mooc2-ans/work/library/review-work"
    f"?courseid={COURSEID}&clazzid={CLAZZID}&workId={WORK_ID}"
    "&workAnswerId={wid}&groupId=0&from=&sort=0&order=0&status=0"
    "&pages=1&size=20&topicid=0"
)

todo = []
for sid, score in SCORES.items():
    wid = WORK_ANSWER_IDS.get(sid)
    if wid:
        todo.append({"sid": sid, "score": score, "wid": wid})

results = []
for i, student in enumerate(todo):
    url = BASE_URL.format(wid=student["wid"])
    cdp("Page.navigate", url=url)
    time.sleep(3)

    # 关键：必须同时设置三个地方
    js(f"""
        var qInput = document.querySelector('input.questionScore');
        if (qInput) {{
            qInput.value = '{student["score"]}';
            $(qInput).trigger('input').trigger('change').trigger('keyup').trigger('blur');
        }}
        $('#tmpscore').val('{student["score"]}');
        $('#score').val('{student["score"]}');
    """)
    time.sleep(1)

    js("markAction(1)")
    time.sleep(3)

    results.append(f"{student['sid']}: {student['score']} submitted")
    if (i + 1) % 5 == 0:
        print(f"Progress: {i+1}/{len(todo)}")

print("\n=== Done ===")
for r in results:
    print(r)

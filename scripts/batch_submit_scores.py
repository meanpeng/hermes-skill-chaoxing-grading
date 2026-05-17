#!/usr/bin/env python3
"""
批量提交分数到超星学习通。
用法：修改 scores 字典和 URL 参数后，在 browser-harness 中执行。

前置条件：
- 已登录学习通（cookies 已注入浏览器）
- 已获取所有学生的 workAnswerId（从批改列表页提取）

安全默认值：
- 本脚本默认只预览待提交清单，不会写入成绩。
- 只有把 CONFIRM_SUBMIT 改为 True，并确认清单无误后，才会调用 markAction(1)。
"""

import json
import sys
import time

# ===== 配置区（使用前填写实际值） =====
COURSEID = ""   # 课程ID
CLAZZID = ""    # 班级ID
CPI = ""        # CPI
WORK_ID = ""    # 作业ID

# ⚠️ 最后一层保险：保持 False 时只打印清单，不会导航、填分或提交。
CONFIRM_SUBMIT = False

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

def fail(message):
    print(f"ERROR: {message}")
    sys.exit(1)


def validate_config():
    missing = [
        name for name, value in {
            "COURSEID": COURSEID,
            "CLAZZID": CLAZZID,
            "WORK_ID": WORK_ID,
        }.items()
        if not str(value).strip()
    ]
    if missing:
        fail("请先填写配置项: " + ", ".join(missing))
    if not SCORES:
        fail("SCORES 为空，没有可提交的分数。")
    if not WORK_ANSWER_IDS:
        fail("WORK_ANSWER_IDS 为空，无法定位学生提交。")


def normalize_todo():
    todo_list = []
    missing_wids = []
    for sid, score in SCORES.items():
        wid = WORK_ANSWER_IDS.get(sid)
        if wid is None:
            missing_wids.append(sid)
            continue
        try:
            numeric_score = float(score)
        except (TypeError, ValueError):
            fail(f"{sid} 的分数不是数字: {score!r}")
        if not 0 <= numeric_score <= 100:
            fail(f"{sid} 的分数超出 0-100 范围: {score!r}")
        todo_list.append({"sid": str(sid), "score": numeric_score, "wid": str(wid)})
    if missing_wids:
        fail("以下学号缺少 workAnswerId: " + ", ".join(map(str, missing_wids)))
    if not todo_list:
        fail("没有有效的待提交记录。")
    return todo_list


# ===== 提交逻辑 =====
BASE_URL = (
    "https://mooc2-ans.chaoxing.com/mooc2-ans/work/library/review-work"
    f"?courseid={COURSEID}&clazzid={CLAZZID}&workId={WORK_ID}"
    "&workAnswerId={wid}&groupId=0&from=&sort=0&order=0&status=0"
    "&pages=1&size=20&topicid=0"
)

validate_config()
todo = normalize_todo()

print("=== 待提交清单 ===")
for student in todo:
    print(f"{student['sid']}: {student['score']:g} (workAnswerId={student['wid']})")

if not CONFIRM_SUBMIT:
    print("\nDRY RUN: CONFIRM_SUBMIT=False，未导航、未填分、未提交。")
    print("确认无误后，再把 CONFIRM_SUBMIT 改为 True 并重新运行。")
    sys.exit(0)

if "cdp" not in globals() or "js" not in globals():
    fail("当前环境缺少 browser-harness 的 cdp/js 函数，不能提交。")

results = []
for i, student in enumerate(todo):
    url = BASE_URL.format(wid=student["wid"])
    cdp("Page.navigate", url=url)
    time.sleep(3)

    # 关键：必须同时设置三个地方
    score_json = json.dumps(student["score"])
    js(f"""
        var qInput = document.querySelector('input.questionScore');
        if (qInput) {{
            qInput.value = String({score_json});
            $(qInput).trigger('input').trigger('change').trigger('keyup').trigger('blur');
        }}
        $('#tmpscore').val(String({score_json}));
        $('#score').val(String({score_json}));
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

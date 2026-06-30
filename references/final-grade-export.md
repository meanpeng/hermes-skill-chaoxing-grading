# 期末成绩数据导出

从超星/学习通“学情统计”一键导出某个班级的**作业统计、考试统计、签到详情统计**，用于后续期末成绩汇总。

## 快速使用

```bash
cd ~/.agents/skills/chaoxing-assignment-grading
.venv/Scripts/python.exe scripts/export_final_grade_data.py \
  --courseid 204565237 \
  --clazzid 139247042 \
  --cpi 492206399 \
  --output all.xlsx
```

输出文件 `all.xlsx` 包含三个 sheet：

- `作业统计`
- `考试统计`
- `签到详情统计`

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--courseid` | 课程 ID | `204565237` |
| `--clazzid` | 班级 ID | `139247042` |
| `--cpi` | 当前用户 ID | `492206399` |
| `--cookie-file` | Cookie 文件路径 | `cx_cookies.txt` |
| `--output` | 输出文件路径 | `all.xlsx` |
| `--tables` | 导出的表 ID，逗号分隔 | 默认 `7,8,12` |
| `--poll-interval` | 轮询间隔（秒） | 默认 `3` |
| `--poll-max` | 最大轮询次数 | 默认 `20` |

## 底层 API

### 1. 触发导出

```text
GET https://stat2-ans.chaoxing.com/teach-data/export
  ?courseid=<courseid>
  &clazzid=<clazzid>
  &seltables=7,8,12
  &cpi=<cpi>
  &ut=t
  &type=1
  &exportType=2
  &fr=stat2
```

返回：

```json
{"status":true}
```

### 2. 轮询下载中心

```text
GET https://mooc2-ans.chaoxing.com/mooc2-ans/tcm/downloadcenter
  ?courseId=<courseid>
  &pageNum=1
  &cpi=<cpi>
  &order=down
```

在返回的 HTML 中查找 `fystat-ans.chaoxing.com/api/export` 的链接。

### 3. 下载文件

直接访问第 2 步得到的 `fystat-ans.chaoxing.com/api/export?...` 链接即可下载 Excel。

## seltables 对应关系

| seltables | sheet 名称 | 说明 |
|-----------|-----------|------|
| `7` | `作业统计` | 各次作业的成绩、提交时间、状态 |
| `8` | `考试统计` | 各次考试的成绩、领取/提交时间、状态 |
| `12` | `签到详情统计` | 每次签到/考勤的状态 |

## 备注

- 该导出为**只读操作**，不会修改任何成绩。
- Cookie 需要提前通过 `scripts/chaoxing_login_cookie.py` 保存。
- 该脚本不处理格式转换；如需把导出结果适配到特定汇总脚本，请在外部处理。

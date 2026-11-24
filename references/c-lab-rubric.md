# C语言实验 报告评分规则与流水线（课程级标准）

> 教师 2026-11-24 定稿。适用于 C语言程序设计（通信 2603）各次实验报告；换实验只改 `rubric.json` 的
> 项目定义和权重，**架构不变**。流程：flash 子代理逐生识图判定 → 脚本汇总算分 → 我复核抄袭/异常 → 教师确认 → 写入超星。

## 一、评分架构（满分≈95，上限 95）

| 项 | 分 | 标准 |
|---|---|---|
| 基础提交 | 41 | 按模板完整提交（封面/项目/目的/原理/步骤/代码） |
| 程序实做 | 25 | 截图里有 **gcc 运行输出**才算；只贴代码不算；找错演示的错误输出不算跑通 |
| 自有内容 | 6 | 实验二=改数据档：≥2 程序自己改 6 / 1 程序 3 / 仅指导书建议值 1 / 全默认 0；实验一=card.c 信息全自己的 6 / 缺项 3 / 张三模板 0 |
| 找错 | 4 项 × 权重 | 终端演示报错/异常输出，或文字写明现象+原因；照抄指导书描述不算。有思考题的实验 ×1.5，没有的 ×3.75 |
| 思考题 | 5 题 × 1.5 | 自己写的答案；一两句极简 ×0.5 |
| 自有文字 | 8 | ≥1500 字 8；1000-1500 6；600-1000 4；300-600 3；<300 1 |
| 加减 | ± | 规范修改记录表 +2；与他人逐字相同段落 −4 |

- 程序/找错/思考题权重是"大多数人都没做就调低"的杠杆：实验二 找错+思考题 13.5 vs 程序+改数据 31。
- 基础 41 的含义：交了完整模板但什么都没跑 ≈ 50-55；5 程序全跑+改数据+薄文字 = 75；再加找错/思考题/文字往上到 90+。
- 规则回代历史 ④ 档（郑子宣 95 / 刘欣月 91 / 周洋 89）吻合，说明与教师手感一致。

## 二、抄袭规则（不套规则分）

**判定（满足任一 = 实锤）**
1. 同字节截图 ≥3 张（校徽、指导书图不算；先做 md5 全班归属，再看独有图）
2. 自有文本逐字相同段落 ≥300 字，或相似 ≥60% 且带相同错字/OCR 痕迹
3. 文件是同一份（下载副本名、同编辑者且内容相同）

**不算**：仅元数据相同、仅数据相同（如奶茶 9.9×36 一组值）、共用模板/指导书步骤、指导书建议值。

**处罚**
| 情形 | 处理 |
|---|---|
| 实锤 | 固定 52-58：有自写内容 58，纯抄 52；判为源头 −2 |
| 共用段落（1 段 ≥300 字相同，其余独立） | −4；2 段以上升为实锤 |
| 方向不明 | 双方按共用段落；有伪装痕迹（大写关键字重排、改文件名、下载副本）的一方判实锤 |
| 无报告只有自己截图 | 60 + FLAG 待教师定（不按交指导书=1 分处理） |

## 三、流水线

```
# 1. 写 rubric.json（换实验只改 items_desc / fixes_desc / questions / weights）
# 2. 导出每生独有截图 + 全文（CRC 容错；同字节图归属、指导书图排除）
python3 scripts/lab_rubric_pipeline.py packets --exp exp2 --dir ~/clang_exp2_grading \
    --guide 指导书_实验二.docx --rubric rubric.json --out packets/exp2
# 3. 子代理判定：glm-5.3-flash（delegation.model），每任务 ≤3 人且 ≤22 张图，并发 ≤4
#    每生：read report.txt → 每图 vision_analyze → 写 results/<exp>/<sid>.json（schema 见脚本头）
# 4. 汇总
python3 scripts/lab_rubric_pipeline.py score --exp exp2 --dir ~/clang_exp2_grading \
    --packets packets/exp2 --results 'results/exp2/*.json' --rubric rubric.json
#    输出 table.csv（规则分）+ pairs.json（文本 ≥300 字逐字相同对）；index.json 里有 image_clusters
# 5. 我复核：pairs.json / image_clusters 套抄袭规则 → 定实锤/共用段落 → 调整 → 教师确认 → submit_scores.py 写入 + 回读核验
```

### 子代理判定要点（写进每个任务）
- 只给 report.txt 路径 + 图片路径，不喂历史分数；明确"done 仅当截图里有 gcc 运行输出"。
- 一图一调 vision_analyze，每轮 3-4 张；429 等 20s 重试。
- 10 个 5.4 并发会撞账户级 429——flash + 并发 4 没问题；glm-5.4 做识图一次别超 3 路。
- 子代理自报"写了文件"不算数：汇总前 `ls results/<exp> | wc -l` 对齐人数，缺的重派。

### 我（主代理）的职责
- 派发前：人数/图数对齐、分组不超限；派发后：只做汇总和异常复核，不替子代理看图。
- 复核三件事：① pairs.json + image_clusters 套抄袭规则；② 规则分与证据明显不符的（如 items 全 true 但 own_chars=115）；③ 文本极长但 ai_traces 的。
- 最终分是否 `max(旧分, 新分)` 由教师当场定（默认重判=不参考旧分）。

### 子代理判定 prompt 模板（第一遍；换实验只替换【实验要求】块，其余照抄）

> 这些规则都是踩坑踩出来的，别在跑完后打补丁——派任务时就带上：
> ① **合并程序规则**（一张截图里一个程序同时做了多个任务，几个都算）；
> ② **目录/文件名不扣分**（只要程序功能和运行输出对得上就算）；
> ③ **找错/思考题只看 own.txt + 截图**（report.txt 里含指导书题目原文，子代理会把它当成"做了"）；
> ④ **未做的不要列进 fixes/questions**（列了也要靠 how/quality 非空才算，容易被误计）；
> ⑤ 无独有截图的学生只按文本判（截图与他人同字节的 items 全 false）。

```
你是 C语言「<实验名>」报告评分助手，逐生判定后写 JSON。只做识图+读文本，不参考任何已有分数。识图用 vision_analyze（一图一调，每轮 3-4 张并行）；报错(如 429)就等 20s 重试一次。
【实验要求】<从 rubric.json 的 items_desc / own_content_desc / fixes_desc / questions 生成>
【判定标准】items.done=true 仅当截图里有该项对应的 gcc 运行输出/证据（只贴代码无输出不算；找错演示的错误输出不算程序跑通）。
**合并程序规则：一张截图里一个程序跑出的输出如果同时覆盖多个任务（如 main.c 先输出 hello 再输出名片；变量程序里又算了平均分；gcc -v 和 settings.json 同屏），那几个任务都算 done=true。**
**目录/文件名不是指导书要求的（如非 D:\CCode\exam2、文件不叫 variables.c）不扣分，只要程序功能和运行输出对得上就算 done。**
【每个学生目录】<packets>/<sid>/ ：report.txt = 报告全文（含指导书步骤）；own.txt = 扣掉指导书原文后的学生自有文字；NN.png = 该生独有截图。
**找错/思考题只看 own.txt 和截图**——report.txt 里的找错题目/思考题原文是指导书内容，不算学生做的。算做了 = 终端演示了报错/异常输出，或 own.txt 里用自己话写了现象+原因+改正；思考题要自己写的答案（一两句极简 = brief）。
【步骤】每生：read own.txt（必要时看 report.txt 了解结构）→ 每张图 vision_analyze（问：软件界面、.c 文件名、终端路径、代码要点、运行输出逐行；有没有合并程序）→ 判定。
【输出】每人一个 JSON 写到 <results>/<exp>/<sid>.json：
{"sid","name","items":[{"key":"<key1>","done":true,"evidence":"img03: <输出行>"}, ...共 N keys],
 "own_content":{"level":2,"evidence":""},"fixes":[{"n":1,"how":"terminal|text","evidence":""}],
 "questions":[{"n":1,"quality":"full|brief","evidence":""}],"text":{"ai_traces":false,"notes":""},"plagiarism_notes":"","flags":""}
**未做的找错/思考题不要列进 fixes/questions。** 最终回复只回 {"written":["sid",...]}。
【学生】<sid> <姓名> <dir> (<n>图；无独有截图的写"无独有截图，只按文本判")；...
```

**第二遍（合并程序复核）** 只在用户点名或第一遍明显偏严时跑：对"程序分未满且有独有截图"的学生，带上第一遍已 done 列表，只问"未完成项是否在合并程序/同屏里也被演示了"；合并时**只采纳 items 变化，own_content 沿用第一遍**（第二遍对改数据档口径不稳）。

### 派发脚本
`lab_rubric_pipeline.py tasks --exp exp2 --rubric rubric.json --packets packets/exp2 [--pass2 --results results/exp2]`
按 ≤3 人且 ≤22 张图自动分组，把每个任务的 context 写到 `tasks/<exp>_T<n>.txt`，派发时整段粘进 delegate_task 的 context 即可。

## 四、已踩的坑
- 文本正则判"输出/找错/思考题"会漏掉只出现在截图里的结果、也会被 OCR 指导书/AI 文本误报——判定必须识图 + 读文本。
- "全班共有的截图"统计会把校徽算进去；要用 md5 归属看具体哪张共享。
- docx 图片 CRC 损坏（张皓月/袁雨杨）会让 zipfile 静默跳过——读 media 用 CRC 容错。

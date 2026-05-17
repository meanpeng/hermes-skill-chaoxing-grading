# hermes-skill-chaoxing-grading

超星学习通（Chaoxing/Xuexitong）教师端作业批量批改技能 — 专为 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 设计。

## 功能

- 🔐 自动登录超星学习通（AES 加密 + Cookie 注入）
- 📚 浏览课程列表，选择目标课程
- 👥 按班级筛选作业
- 📦 批量下载作业包（.docx / .doc）
- 🔍 抽样分析作业质量，建议评分标准
- ✅ 全量自动批改打分
- 📤 批量提交分数到学习通

## 安装

### 方法 1：Hermes CLI 安装（推荐）

```bash
hermes skill install meanpeng/hermes-skill-chaoxing-grading
```

### 方法 2：手动安装

```bash
# 克隆到本地 skills 目录
git clone https://github.com/meanpeng/hermes-skill-chaoxing-grading.git ~/.hermes/skills/productivity/chaoxing-assignment-grading
```

## 前置条件

1. **Hermes Agent** 已安装（[安装指南](https://hermes-agent.nousresearch.com/docs)）
2. **browser-harness** 已安装（用于浏览器自动化）
3. **Python 依赖**：
   ```bash
   pip install python-docx olefile pycryptodome
   ```

## 使用方法

在 Hermes Agent 中直接说：

```
帮我看XX课程的作业
批改人工智能应用基础课程信工2502班的实验报告一
```

或者使用完整流程：

```
用 188xxx 登录超星学习通，批改人工智能应用基础课程信工2502班的实验报告一
```

## 目录结构

```
.
├── SKILL.md                              # 主技能文件（Hermes Agent 读取）
├── scripts/
│   ├── batch_grade.py                    # 批量分析作业脚本
│   └── batch_submit_scores.py            # 批量提交分数脚本
├── README.md                             # 本文件
└── LICENSE                               # MIT 许可证
```

## 技术细节

- 登录使用 AES-CBC 加密（key: `u2oh6Vu^HWe4_AES`）
- Cookies 通过 CDP `Network.setCookie` 注入浏览器
- 支持 `.docx`（python-docx）和 `.doc`（OLE2 解析）两种格式
- 超星实验报告使用表格布局，必须同时读取 paragraphs 和 table cells

## 常见问题

### 登录失败？
- 超星对 headless Chrome 返回空 body，必须用 curl 登录后注入 cookies
- `p_auth_token` 和 `vc3` 是 httpOnly cookies，只能通过 CDP 设置

### 作业下载慢？
- packWork 调用后等待 15 秒再查 download center
- 大文件可能需要更长时间（最多 12 小时）

### 分数提交不生效？
- 必须同时设置 `input.questionScore`、`#tmpscore`、`#score` 三个地方
- 只设置 `questionScore` 不够

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 作者

闵鹏 (Min Peng) - 成都锦城学院教师

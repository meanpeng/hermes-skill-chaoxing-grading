# chaoxing-assignment-grading

超星学习通（Chaoxing/Xuexitong）教师端作业批量批改工具。

**适用于任何 AI 智能体（Hermes、Claude、GPT、Gemini 等）或人工操作。**

## 功能

- 🔐 自动登录超星学习通（AES 加密 + Cookie 注入）
- 📚 浏览课程列表，选择目标课程
- 👥 按班级筛选作业
- 📦 批量下载作业包（.docx / .doc）
- 🔍 抽样分析作业质量，建议评分标准
- ✅ 全量自动批改打分
- 📤 批量提交分数到学习通

## 使用方式

### 方式 1：AI 智能体（推荐）

把 `SKILL.md` 的内容作为上下文/系统提示喂给你的 AI 智能体，然后说：

```
帮我看XX课程的作业
批改人工智能应用基础课程信工2502班的实验报告一
用 188xxx 登录超星学习通，批改...
```

支持的智能体：
- **Hermes Agent** — 直接克隆到 `~/.hermes/skills/` 目录即可
- **Claude (Projects)** — 把 SKILL.md 内容放进 Project Knowledge
- **GPT (Custom GPTs)** — 把 SKILL.md 内容放进 Instructions
- **Gemini** — 把 SKILL.md 内容放进 System Instructions
- **Cursor / Windsurf / Aider** — 放进项目根目录作为规则文件
- **其他** — 任何支持长上下文的智能体

### 方式 2：手动使用

直接参考 `SKILL.md` 中的步骤和代码片段，配合浏览器开发者工具手动操作。

## 前置条件

1. **浏览器自动化工具**（如 browser-harness、Playwright、Puppeteer）
2. **Python 依赖**：
   ```bash
   pip install python-docx olefile pycryptodome
   ```

## 目录结构

```
.
├── SKILL.md                              # 完整工作流程（544行，含代码和 Pitfalls）
├── scripts/
│   ├── batch_grade.py                    # 批量分析作业脚本
│   └── batch_submit_scores.py            # 批量提交分数脚本
├── README.md                             # 本文件
└── LICENSE                               # MIT 许可证
```

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/meanpeng/hermes-skill-chaoxing-grading.git
cd hermes-skill-chaoxing-grading
```

### 2. 安装依赖

```bash
pip install python-docx olefile pycryptodome
```

### 3. 使用脚本

```bash
# 批量分析作业（修改脚本中的 BASE_DIR 后运行）
python scripts/batch_grade.py

# 批量提交分数（在 browser-harness 中运行，需先配置 SCORES 和 WORK_ANSWER_IDS）
```

### 4. AI 智能体集成

**Hermes Agent：**
```bash
# 直接克隆到 skills 目录
git clone https://github.com/meanpeng/hermes-skill-chaoxing-grading.git ~/.hermes/skills/productivity/chaoxing-assignment-grading
```

**其他智能体：**
把 `SKILL.md` 的内容复制到你的智能体的知识库/指令中即可。

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

## 贡献

欢迎提交 Issue 和 Pull Request！

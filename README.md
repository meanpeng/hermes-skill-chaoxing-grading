# chaoxing-assignment-grading

超星学习通（Chaoxing/Xuexitong）教师端作业批量批改工具。

**适用于任何 AI 智能体（Hermes、Claude、GPT、Gemini 等）或人工操作。**

## 功能

- 🔐 自动登录超星学习通（AES 加密 + Cookie 注入）
- 📚 浏览课程列表，选择目标课程
- 👥 按班级筛选作业
- 📦 按当前班级批量下载作业附件包（.docx / .doc / 学生 zip）
- 🔍 整理作业文本、图片数量和文件路径，供 agent 逐份阅读
- ✅ 由 agent 阅读报告内容后给出评分建议
- 📤 批量提交分数到学习通（默认 dry-run，需显式确认后才提交）

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
2. **Python 3.11+**（推荐；GBK 文件名 zip 解压在 3.11+ 最稳）
3. **Python 依赖**：
   ```bash
   python -m pip install -r requirements.txt
   ```

## 跨平台兼容性

| 平台 | 状态 | 说明 |
|------|------|------|
| Windows | 支持 | 推荐 PowerShell/cmd 运行 `python ...`；不依赖 `unzip` 或 Bash heredoc |
| Linux | 支持 | 可用系统 Python，也可用虚拟环境 |
| macOS | 支持 | 可用系统 Python 或 Homebrew/pyenv Python |

为保证三端一致，仓库里的辅助脚本都使用 Python 标准库路径处理；登录 cookies 使用 `scripts/chaoxing_login_cookie.py`，作业包解压使用 `scripts/extract_work_zip.py`。

## 目录结构

```
.
├── SKILL.md                              # 完整工作流程（544行，含代码和 Pitfalls）
├── scripts/
│   ├── batch_grade.py                    # 批量整理作业素材脚本
│   ├── batch_submit_scores.py            # 批量提交分数脚本
│   ├── chaoxing_login_cookie.py          # 跨平台登录并保存 cookies
│   └── extract_work_zip.py               # 跨平台解压 GBK 文件名作业包
├── requirements.txt                      # Python 依赖
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
python -m pip install -r requirements.txt
```

### 3. 使用脚本

```bash
# 登录并保存 cookies（不建议把密码写进命令；省略 --password 可隐藏输入）
python scripts/chaoxing_login_cookie.py --phone "手机号" --cookie-file cx_cookies.txt

# 解压作业包，兼容 Windows/Linux/macOS
python scripts/extract_work_zip.py output.zip -d output_dir

# 批量整理作业素材，生成供 agent 逐份阅读的 CSV（默认）
python scripts/batch_grade.py --base-dir output_dir

# 可选：用户明确选择“指标辅助评分”时，额外输出粗略指标信号
python scripts/batch_grade.py --base-dir output_dir --mode metrics

# 批量提交分数（在 browser-harness 中运行，需先配置 SCORES 和 WORK_ANSWER_IDS）
# 默认 CONFIRM_SUBMIT=False，只打印清单；最终确认后再改为 True
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
- 超星“仅附件”导出可能是“每个学生一个 zip”，`batch_grade.py` 会自动展开这些学生 zip 后整理报告路径、文本预览和图片数量
- 默认评分方式是 agent 逐份阅读；只有用户明确选择时，才使用 `--mode metrics` 输出粗略指标辅助初筛

## 常见问题

### 登录失败？
- 超星对 headless Chrome 返回空 body，建议用 `scripts/chaoxing_login_cookie.py` 登录后注入 cookies
- `p_auth_token` 和 `vc3` 是 httpOnly cookies，只能通过 CDP 设置
- 不要把账号密码写进仓库、日志或提交脚本；确认账号时只展示脱敏手机号

### 作业下载慢？
- 导出作业附件是按当前筛选班级导出，不是整门课全部班级；触发导出前先确认当前班级名、`clazzid` 和 `workid`
- packWork 调用后等待 15 秒再查 download center
- 大文件可能需要更长时间（最多 12 小时）
- 下载后的作业包优先用 `scripts/extract_work_zip.py` 解压；脚本会自动兼容 UTF-8 标志文件名和常见 GBK 文件名

### 分数提交不生效？
- 必须同时设置 `input.questionScore`、`#tmpscore`、`#score` 三个地方
- 只设置 `questionScore` 不够
- 使用 `scripts/batch_submit_scores.py` 时先看 dry-run 清单，确认后再把 `CONFIRM_SUBMIT` 改为 `True`

## 许可证

MIT License - 详见 [LICENSE](LICENSE)


## 贡献

欢迎提交 Issue 和 Pull Request！

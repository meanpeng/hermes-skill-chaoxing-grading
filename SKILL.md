---
name: chaoxing-assignment-grading
description: "Use when grading Chaoxing/Xuexitong assignments. Teacher workflow: login, browse courses, download submissions, analyze quality, auto-grade, submit scores."
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [chaoxing, xuexitong, grading, education, assignment, automation]
    related_skills: [browser-harness]
---

# 超星学习通作业批改

教师端完整流程，每一步都需要用户确认后才继续。

## 核心原则：交互式确认流程

**严格按以下 6 步执行。但有一个重要例外：**

- **如果用户在提示词中已经明确了某个步骤的选择（如账号密码、课程、班级、作业等），则该步骤直接执行，不再重复询问。**
- **唯一不可跳过的确认：第 6 步提交分数，无论什么情况都必须等用户明确确认后才能提交。**

示例：
- 用户说「用 188xxx 登录，批改人工智能应用基础课程信工2502班的实验报告一」→ 跳过第1/2/3步的询问，直接执行
- 用户只说「帮我看作业」→ 按流程逐步询问
- 无论哪种情况，第5步展示结果后、第6步提交前，都必须停下来问用户确认

---

## 第 1 步：确认登录账号

1. 从 memory 中查找用户是否已保存过超星账号密码
2. 如果有，直接展示给用户确认：「已找到保存的账号：手机号 xxx，密码 xxx。用这个登录吗？」
3. 如果没有，或用户说不对，询问用户获取正确的账号密码
4. **用户确认后** → 执行登录流程

### 登录技术细节

超星服务器对 headless Chrome 返回空 body（反Bot检测）。解决方案：
1. 用 `curl` 拿到完整登录页 HTML
2. AES 加密账号密码（key: `u2oh6Vu^HWe4_AES`，CBC模式，iv=key）
3. 用 curl 调 `/fanyalogin` API 登录
4. 拿到 cookies 后用 CDP `Network.enable` + `Network.setCookie` 注入浏览器

```python
# 推荐方式：用 Python http.cookiejar 登录（自动保存完整 cookies，不会截断 p_auth_token）
python3 << 'PY'
from Crypto.Cipher import AES
import base64, urllib.request, urllib.parse, http.cookiejar

key = b"u2oh6Vu^HWe4_AES"
iv = key
def encrypt(text):
    text_bytes = text.encode('utf-8')
    pad_len = 16 - (len(text_bytes) % 16)
    padded = text_bytes + bytes([pad_len] * pad_len)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return base64.b64encode(cipher.encrypt(padded)).decode()

phone_enc = encrypt('手机号')
pwd_enc = encrypt('密码')

data = urllib.parse.urlencode({
    'fid': '-1', 'uname': phone_enc, 'password': pwd_enc,
    'refer': 'https://i.chaoxing.com', 't': 'true',
    'doubleFactorLogin': '0', 'forbidotherlogin': '0',
    'independentId': '0', 'independentNameId': '0',
}).encode()

req = urllib.request.Request(
    "https://passport2.chaoxing.com/fanyalogin", data=data,
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://passport2.chaoxing.com',
    })

cj = http.cookiejar.MozillaCookieJar('/tmp/cx_cookies_fresh.txt')
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
resp = opener.open(req)
print(resp.read().decode())  # {"url":"https://i.chaoxing.com","status":true}
cj.save(ignore_discard=True, ignore_expires=True)
print(f"Saved {len(cj)} cookies")
PY

# 注入 cookies 到浏览器
BU_CDP_URL=http://127.0.0.1:9222 browser-harness <<'PYEOF'
import json, time, http.cookiejar

cj = http.cookiejar.MozillaCookieJar('/tmp/cx_cookies_fresh.txt')
cj.load(ignore_discard=True, ignore_expires=True)

ensure_real_tab()
cdp("Network.enable")

for c in cj:
    cookie = {
        "name": c.name, "value": c.value, "domain": c.domain,
        "path": c.path, "secure": c.secure, "httpOnly": True,
    }
    if c.expires:
        cookie["expires"] = c.expires
    cdp("Network.setCookie", **cookie)
    print(f"Injected: {c.name}")

cdp("Page.navigate", url="https://i.chaoxing.com")
time.sleep(6)
print(js("document.title"))  # 应显示 "🐴 个人空间"
PYEOF
```

### Mark 页面参数提取 Pitfall
- **⚠️ 全局 JS 变量不可靠**：在 mark 页面用 `js("typeof courseId")` 等方式获取全局变量，可能返回 `undefined` 或 `{}`。原因是这些变量可能在闭包或 jQuery 命名空间内定义。
- **✅ 用 hidden inputs 提取**：页面上有大量 `<input type="hidden">`，包含所有关键参数：
  ```python
  hidden = js("""
  var inputs = Array.from(document.querySelectorAll('input[type=hidden]'));
  var result = {};
  inputs.forEach(i => { if (i.name) result[i.name] = i.value; });
  JSON.stringify(result);
  """)
  # 可靠获取: courseid, clazzid, workid, cpi, taskId, uid, currentClassId, currentClassName 等
  ```

### Review 按钮点击 Pitfall
- work list 页面的 Review 按钮是 `<a onclick="toMarkWork(this)" data="/mooc2-ans/work/library/review-work?...">` 形式
- 点击特定作业的 Review：需匹配父行中包含作业名文本的按钮：
  ```python
  js("""
  var links = Array.from(document.querySelectorAll('a[onclick*="toMarkWork"]'));
  var target = links.find(a => {
      var row = a.closest('tr') || a.closest('div');
      return row && row.innerText.includes('目标作业名');
  });
  if (target) target.click();
  """)
  ```
- 或者直接获取所有 Review 按钮的 `data` 属性，按页面顺序第一个即为最新作业

### 登录 Pitfalls
- `Network.setCookie` 需先调 `Network.enable`，否则报 `Unknown Network method`
- httpOnly cookies（`vc3`, `p_auth_token`）只能通过 CDP 设置，不能用 `document.cookie`
- `new_tab()` 在某些 Chrome 版本报 `Unknown Target method: activateTarget`，用 `ensure_real_tab()` + `cdp("Page.navigate")` 替代
- 每次 `browser-harness` 调用都要带 `ensure_real_tab()`，防止会话过期
- **先检查 cookies 是否过期**：`curl -s -b /tmp/chaoxing_cookies.txt "https://i.chaoxing.com" -o /dev/null -w "%{http_code}"`。302 = 过期，需重新登录；200 = 有效，可直接跳到步骤 2。不要盲目假设 cookies 有效或无效。
- **⚠️ curl `-c` 会截断长 cookie 值**：`p_auth_token` 和 `vc3` 是很长的字符串，curl 的 `-c` cookie 文件可能截断它们。**必须用 Python `http.cookiejar.MozillaCookieJar` 保存 cookies**。

---

## 第 2 步：确认目标课程

登录成功后，列出所有课程让用户选择：

1. 导航到课程列表页
2. 提取所有课程名称
3. 用列表展示给用户，询问：「请问要批改哪个课程的作业？」
4. **用户确认后** → 进入该课程

```python
# 进入课程列表页
cdp("Page.navigate", url="https://mooc2-ans.chaoxing.com/visit/interaction?fid=YOUR_FID")
time.sleep(8)

# 获取所有课程
courses = js("""
Array.from(document.querySelectorAll('a'))
  .filter(a => a.href.includes('courseId'))
  .map(a => ({text: a.innerText.trim(), href: a.href}))
  .filter(x => x.text.length > 1)
""")
```

### 关键 URL
- **课程列表**: `https://mooc2-ans.chaoxing.com/visit/interaction?fid=YOUR_FID`
- **课程主页**: `https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/tch?courseid=xxx&clazzid=xxx&cpi=xxx`
- **作业列表**: `https://mooc2-ans.chaoxing.com/mooc2-ans/work/list?courseid=xxx&clazzid=xxx&cpi=xxx`

---

## 第 3 步：确认班级和作业

进入课程后，列出该课程的作业和班级，让用户选择：

1. 获取该课程的所有作业列表
2. 获取该课程的所有班级
3. 展示给用户：「找到以下作业：... 和以下班级：... 请问要批改哪个班的哪份作业？」
4. **用户确认后** → 筛选班级，进入作业页面

### 班级筛选
作业列表页有班级筛选下拉框 `li.classli`，点击即可切换班级。

**直接 URL 筛选**：在 work list URL 中加 `selectClassid=班级ID` 可直接跳到指定班级：
```
https://mooc2-ans.chaoxing.com/mooc2-ans/work/list?courseid=XXX&selectClassid=YYY&cpi=ZZZ&status=-1&v=0&topicid=0
```

```python
# 筛选班级
js("""
var items = Array.from(document.querySelectorAll('li.classli'));
var target = items.find(el => el.innerText.trim().includes('目标班级名'));
if (target) target.click();
""")
```

---

## 第 4 步：下载作业 & 抽样分析，确定批改标准

**这是最关键的一步，不要急着全量批改。**

### 4a. 下载作业包

```python
# 1. 触发打包（完整答题记录 + PDF）
result = js("""
new Promise((resolve) => {
    $.ajax({
        type: 'get', url: '/mooc2-ans/work/packWork',
        data: {
            'courseid': courseId, 'clazzid': clazzId, 'workid': workId,
            'type': 0, 'uid': uid, 'fid': fid,
            'onlyattachment': '1',  # 仅附件，文件更小
            'taskId': taskId,
            'isPdf': '1',
            'packtype': '1',
            'customNameGroup': '', 'wordCustomFormat': '', 'personIds': ''
        },
        success: function(data) { resolve('SUCCESS: ' + data); },
        error: function(xhr, s, e) { resolve('ERROR: ' + xhr.status); }
    });
});
""")

# 2. 获取下载链接
dl_html = js("""
new Promise((resolve) => {
    $.ajax({
        url: '/mooc2-ans/tcm/downloadcenter',
        data: {'courseId': courseId, 'pageNum': 1, 'cpi': cpi, 'order': 'down'},
        dataType: 'html',
        success: function(data) { resolve(data); }
    });
});
""")
import re
download_urls = re.findall(r'href="(https://fanyadata\.chaoxing\.com/workzip/[^"]+)"', dl_html)

# 3. 下载并解压
curl -L -o output.zip "下载URL" -H "User-Agent: Mozilla/5.0"
unzip -O GBK -o output.zip -d output_dir/
```

### 下载作业包 Pitfall
- packWork 调用后，等待 **15 秒** 再查 download center 通常即可拿到下载链接，无需反复轮询
- download center HTML 中，**按时间倒序排列**，第一个匹配 `workzip/fanyadata.chaoxing.com` 的 URL 即为最新打包
- URL 中的 `fn=` 参数包含中文文件名（URL 编码），可用于确认是否为目标作业
- 如果 packWork 返回 `"status":"1"` 且提示"后台处理"，说明文件较大，可能需要等更久（最多 12 小时）

### 4b. 抽样 3-5 个学生，分析质量分布

从作业中选取 3-5 个有代表性的样本（时间分散：早/中/晚各一个），提取文字+图片。

**⚠️ 关键：必须同时支持 .docx 和 .doc 格式！** 超星学生可能提交任一种格式。用以下统一函数自动处理：

```python
import os, struct
from docx import Document

def get_report_text(student_dir):
    """自动检测 .docx/.doc 并提取全部文字（段落 + 表格单元格）
    
    ⚠️ 部分学校的实验报告模板使用表格布局，内容可能在 table cells 里！
    只读 paragraphs 会得到 150-200 字的空表头。
    
    优先 .docx（python-docx 提取更完整），fallback 到 .doc（OLE2 解析）。
    返回 (text, file_path, format_type)。
    """
    files = os.listdir(student_dir)
    
    # 1) 优先找 .docx（排除模板文件如 "实验报告V2024.docx"）
    report_docxs = [f for f in files if f.endswith('.docx') and not any(
        kw in f for kw in ['V2024', '模板', 'template']
    )]
    # 如果过滤后没有，再用所有 .docx
    if not report_docxs:
        report_docxs = [f for f in files if f.endswith('.docx')]
    
    for f in report_docxs:
        path = os.path.join(student_dir, f)
        try:
            doc = Document(path)
            texts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    texts.append(para.text.strip())
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            texts.append(cell.text.strip())
            text = "\n".join(texts)
            if len(text) > 50:  # 有效内容 > 50 字才用
                return text, path, 'docx'
        except Exception:
            pass
    
    # 2) Fallback: .doc (OLE2 格式)
    import olefile
    report_docs = [f for f in files if f.endswith('.doc') and not f.endswith('.docx')]
    for f in report_docs:
        path = os.path.join(student_dir, f)
        try:
            ole = olefile.OleFileIO(path)
            if not ole.exists('WordDocument'):
                continue
            raw = ole.openstream('WordDocument').read()
            text_parts, current = [], []
            i = 0
            while i < len(raw) - 1:
                char = struct.unpack('<H', raw[i:i+2])[0]
                if (0x20 <= char <= 0x7E or 0x4E00 <= char <= 0x9FFF or
                    0x3000 <= char <= 0x303F or 0xFF00 <= char <= 0xFFEF or
                    char in (0x0D, 0x0A, 0x09)):
                    current.append(chr(char))
                else:
                    if len(current) > 3:
                        text_parts.append(''.join(current))
                    current = []
                i += 2
            if len(current) > 3:
                text_parts.append(''.join(current))
            text = '\n'.join(text_parts)
            if len(text) > 50:
                return text, path, 'doc'
        except Exception:
            pass
    
    return "", None, "none"

def count_report_images(student_dir, format_type, report_path):
    """统计报告中的图片数量，自动处理 .docx 和 .doc"""
    if format_type == 'docx':
        try:
            doc = Document(report_path)
            return sum(1 for rel in doc.part.rels.values() if "image" in rel.reltype)
        except Exception:
            return 0
    elif format_type == 'doc':
        # .doc 图片：通过文件大小估算（1.9MB 约 6-15 张图，纯文字通常 < 200KB）
        size = os.path.getsize(report_path)
        if size > 500000:  # > 500KB 大概率有图片
            return max(3, min(15, (size - 200000) // 150000))
        return 0
    return 0
```

### 4c. 向用户报告分析结果，建议评分标准

向用户汇报抽样结果，格式如下：

「我先看了 5 个同学的作业，情况如下：
| 学生 | 字数 | 图片 | 章节完整度 | 内容质量 |
|------|------|------|-----------|---------|
| 学生A | 3000字 | 15张 | 6/6 完整 | 详实，有代码有结果 |
| 学生B | 1200字 | 8张 | 5/6 缺总结 | 较完整但总结简略 |
| ...

根据分析，我建议的批改标准：
- **宽松模式**：最优 100 分，大部分人 85-95，最低不低于 75
- **严谨模式**：最优 100 分，拉开梯度，70-100 分分布

请问用哪种模式？还是你有具体的评分要求？」

**用户确认评分标准后**，再进入下一步。

### 4d. 建立评分维度

根据用户选择的标准和作业类型，建立评分维度。示例（实验报告类）：

| 维度 | 权重 | 说明 |
|------|------|------|
| 章节完整性 | 20% | 各章节是否齐全 |
| 文字内容量 | 15% | 表格内文字总字数（不含表头） |
| 实验步骤详实度 | 25% | 实验步骤与结果的内容量和质量 |
| 截图证据 | 20% | 代码/规则截图 + 运行结果 + 可视化图谱 |
| 实验总结 | 10% | 总结是否有反思和收获 |
| 格式规范 | 10% | 表头填写完整、排版清晰 |

---

## 第 5 步：全量批改 & 展示结果

1. 按确认的评分标准全量分析打分
2. 生成评分报告（CSV 格式）
3. **展示给用户确认**：「批改完成，共 XX 份作业。分数分布如下：
   - 100 分：X 人
   - 90-99 分：X 人
   - 80-89 分：X 人
   - 70-79 分：X 人
   - 最低分：XX 分（学生XXX）

   详细报告已生成，需要我调整分数吗？确认后我会提交到学习通。」

### 批量批改技术细节

```python
# 处理 .doc（OLE2 旧格式）文件
import olefile, struct

def extract_doc_text(filepath):
    """从 .doc (OLE2) 文件提取文字"""
    ole = olefile.OleFileIO(filepath)
    if not ole.exists('WordDocument'):
        return ""
    raw = ole.openstream('WordDocument').read()
    text_parts, current = [], []
    i = 0
    while i < len(raw) - 1:
        char = struct.unpack('<H', raw[i:i+2])[0]
        if (0x20 <= char <= 0x7E or 0x4E00 <= char <= 0x9FFF or
            0x3000 <= char <= 0x303F or char in (0x0D, 0x0A, 0x09)):
            current.append(chr(char))
        else:
            if len(current) > 3:
                text_parts.append(''.join(current))
            current = []
        i += 2
    if len(current) > 3:
        text_parts.append(''.join(current))
    return '\n'.join(text_parts)
```

### 批改 Pitfalls
- DOCX 文件名可能是 GBK 编码（`unzip -O GBK`）
- **⚠️ 部分学校的实验报告模板使用表格布局，内容可能在 table cells 里！** 只读 paragraphs 会得到 150-200 字的空表头
- **⚠️ 学生可能提交 .doc 或 .docx，必须两种都支持**：用 `get_report_text(student_dir)` 自动检测，不要只看 .docx
- **⚠️ .doc 图片无法精确计数**：通过文件大小估算（>500KB ≈ 有图片，纯文字 < 200KB）
- **⚠️ 有些 .docx 文件名含乱码（GBK 编码问题）但内容正常**，不影响文字提取
- **⚠️ 模板文件过滤**：排除文件名含 `V2024`、`模板`、`template` 的 .docx，它们是空模板
- **⚠️ 图片密集型作业**：很多学生文字少但截图多，必须检查图片
- **⚠️ 抄袭检测**：同组学生文件大小完全相同 = 高度可疑，应给相同分数
- **⚠️ 章节缺失 vs 序号缺失**：有些学生有内容但漏标序号，检查关键词
- **⚠️ 宽松评分**：作业不是考试，最优 100 分，多给几个 100，最低不低于 70-75

---

## 第 6 步：用户确认后提交分数

**⚠️ 必须等用户明确说「确认」「可以提交」「提交吧」之后才执行提交。不要自动提交。**

提交方式：浏览器自动化逐个打分

### 6.1 获取学生-workAnswerId 映射

```python
# 在批改列表页提取所有学生的 workAnswerId
students_page1 = js("""
var btns = document.querySelectorAll('a[onclick*="toMarkWork"]');
var result = [];
for (var i = 0; i < btns.length; i++) {
    var data = btns[i].getAttribute('data') || '';
    var match = data.match(/workAnswerId=(\d+)/);
    result.push(match ? match[1] : '');
}
result;
""")

# 姓名/学号提取：从 document.body.innerText 按顺序匹配学号
import re
page_text = js("document.body.innerText")
student_ids = re.findall(r'\b(25\d{7})\b', page_text)
```

### 6.2 分页获取

```python
js("searchMarkList(2)")  # 跳到第 2 页
time.sleep(5)
```

### 6.3 逐个提交分数

```python
base_url = ("https://mooc2-ans.chaoxing.com/mooc2-ans/work/library/review-work"
            "?courseid={cid}&clazzid={clid}&workId={wid}&workAnswerId={waid}"
            "&groupId=0&from=&sort=0&order=0&status=0&pages=1&size=20&topicid=0")

for student in todo_list:
    url = base_url.format(cid=courseid, clid=clazzid, wid=workId, waid=student['wid'])
    cdp("Page.navigate", url=url)
    time.sleep(4)

    # ⚠️ 关键：必须同时设置 visible input + tmpscore + hidden score
    js(f"""
        var qInput = document.querySelector('input.questionScore');
        if (qInput) {{
            qInput.value = '{score}';
            $(qInput).trigger('input').trigger('change').trigger('keyup').trigger('blur');
        }}
        $('#tmpscore').val('{score}');
        $('#score').val('{score}');
    """)
    time.sleep(1)

    js("markAction(1)")
    time.sleep(4)
```

### 提交分数 Pitfalls
- **⚠️ `tmpscore` 必须手动设置**：只设置 `input.questionScore` 不够，必须 `$('#tmpscore').val(score)`
- **⚠️ 首次提交返回列表页**：后续提交需重新导航到下一个学生的 review URL
- **⚠️ 问题 ID 会变**：用 `document.querySelector('input.questionScore')` 选择器比硬编码 ID 更可靠
- **⚠️ 提交后验证**：确认状态变为 "Completed"，如果还是 "To be reviewed" 说明 tmpscore 为空
- **⚠️ 分页**：默认每页 20 条，超过 20 人时需翻页（`searchMarkList(pageNum)`）

---

## 完整交互流程（一图流）

**规则：用户提示词中已明确的信息 → 直接执行不询问；第6步提交 → 必须确认**

```
用户: "帮我看XX课程的作业"
│
├─ 第1步: 账号已明确？→ 直接登录 | 未明确 → 「用账号 188**** 登录超星学习通，对吗？」
│
├─ 第2步: 课程已明确？→ 直接进入 | 未明确 → 列出课程让用户选
│
├─ 第3步: 班级+作业已明确？→ 直接筛选 | 未明确 → 列出班级和作业让用户选
│
├─ 第4步: 先看 3-5 个同学 → 报告分析结果 → 建议评分标准
│  「我建议用宽松模式，还是严谨模式？」
│  └─ 用户确认标准 → 全量批改
│
├─ 第5步: 展示批改结果（分数分布 + 详细报告）
│  「需要调整吗？」
│  └─ 用户确认分数
│
└─ 第6步: ⚠️ 必须确认 → 「确认提交这 XX 份成绩到学习通吗？」
   └─ 用户说"提交" → 执行提交 → 报告完成
```

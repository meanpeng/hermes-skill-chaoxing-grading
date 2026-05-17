#!/usr/bin/env python3
"""
批量整理 Chaoxing 作业附件，给 agent 逐份阅读评分提供素材。
用法：python scripts/batch_grade.py --base-dir "作业解压目录"
输出：控制台汇总 + CSV 素材清单。

⚠️ 自动支持 .docx 和 .doc 格式，无需手动切换。
"""

import os
import csv
import struct
import argparse
import sys
import zipfile


REPORT_TEMPLATE_KEYWORDS = ("V2024", "模板", "template")
STUDENT_ARCHIVE_DIR = "__unzipped__"
SECTION_KEYWORDS = [
    ("basic", ["课程名称", "项目名称", "实验/实训报告", "学生姓名", "学号"]),
    ("purpose_or_type", ["实验目的", "实验类型", "设计性实验", "验证性实验", "项目名称"]),
    ("environment", ["实验环境", "软件环境", "硬件设备", "依赖库", "Python", "numpy", "matplotlib"]),
    ("process", ["实验步骤", "内容及过程记录", "关键函数", "代码解释", "算法流程", "训练过程"]),
    ("result", ["实验结果", "结果与分析", "运行结果", "可视化", "截图", "输出结果"]),
    ("summary", ["实验总结", "心得", "体会", "掌握", "认识到", "收获"]),
]


def open_zip_with_encoding(zip_path, encoding="gbk"):
    """Open zip with GBK fallback while honoring UTF-8 filename flags."""
    with zipfile.ZipFile(zip_path) as probe:
        has_utf8_names = any(info.flag_bits & 0x800 for info in probe.infolist())
    if has_utf8_names:
        return zipfile.ZipFile(zip_path)
    try:
        return zipfile.ZipFile(zip_path, metadata_encoding=encoding)
    except TypeError:
        return zipfile.ZipFile(zip_path)


def safe_extract_zip(zip_path, output_dir, encoding="gbk"):
    """Extract a zip safely, preserving UTF-8 or GBK names as appropriate."""
    base = os.path.abspath(output_dir)
    os.makedirs(base, exist_ok=True)
    with open_zip_with_encoding(zip_path, encoding) as zf:
        for member in zf.infolist():
            target = os.path.abspath(os.path.join(base, member.filename))
            if os.path.commonpath([base, target]) != base:
                raise ValueError(f"Unsafe zip path: {member.filename}")
            zf.extract(member, base)


def prepare_student_dir(student_dir):
    """Return a directory containing files to inspect, expanding nested student zips."""
    if any(f.lower().endswith((".docx", ".doc")) for f in os.listdir(student_dir)):
        return student_dir

    zip_files = [
        f for f in os.listdir(student_dir)
        if f.lower().endswith(".zip") and os.path.isfile(os.path.join(student_dir, f))
    ]
    if not zip_files:
        return student_dir

    expanded = os.path.join(student_dir, STUDENT_ARCHIVE_DIR)
    os.makedirs(expanded, exist_ok=True)
    for zip_name in zip_files:
        safe_extract_zip(os.path.join(student_dir, zip_name), expanded)
    return expanded


def get_report_text(student_dir):
    """自动检测 .docx/.doc 并提取全部文字（段落 + 表格单元格）

    ⚠️ 超星实验报告模板使用表格布局，绝大部分内容在 table cells 里！
    只读 paragraphs 会得到 150-200 字的空表头。

    优先 .docx（python-docx 提取更完整），fallback 到 .doc（OLE2 解析）。
    返回 (text, file_path, format_type)。
    """
    try:
        from docx import Document
    except ImportError:
        Document = None
    try:
        import olefile
    except ImportError:
        olefile = None

    files = os.listdir(student_dir)

    # 1) 优先找 .docx（排除模板文件）
    report_docxs = [f for f in files if f.lower().endswith('.docx') and not any(
        kw in f for kw in REPORT_TEMPLATE_KEYWORDS
    )]
    if not report_docxs:
        report_docxs = [f for f in files if f.lower().endswith('.docx')]

    if Document:
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
                if len(text) > 50:
                    return text, path, 'docx'
            except Exception:
                pass

    # 2) Fallback: .doc (OLE2 格式)
    report_docs = [f for f in files if f.lower().endswith('.doc') and not f.lower().endswith('.docx')]
    if olefile:
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
            from docx import Document
            doc = Document(report_path)
            return sum(1 for rel in doc.part.rels.values() if "image" in rel.reltype)
        except Exception:
            return 0
    elif format_type == 'doc':
        # .doc 图片：通过文件大小估算
        size = os.path.getsize(report_path)
        if size > 500000:
            return max(3, min(15, (size - 200000) // 150000))
        return 0
    return 0


def preview_text(full_text, limit=220):
    """Return a compact text preview for orientation only; not for grading."""
    collapsed = " ".join(line.strip() for line in full_text.splitlines() if line.strip())
    return collapsed[:limit]


def optional_metrics(full_text):
    """Optional rough signals; use only when the user chose metric-assisted grading."""
    section_count = sum(
        1 for _, keywords in SECTION_KEYWORDS
        if any(keyword in full_text for keyword in keywords)
    )
    summary_positions = [
        idx for idx in (
            full_text.find("实验总结"),
            full_text.find("总结"),
            full_text.find("心得"),
        )
        if idx >= 0
    ]
    summary_text = full_text[min(summary_positions):] if summary_positions else ""
    has_reflection = any(k in summary_text for k in [
        "对比", "分析", "差异", "认识", "理解", "掌握", "发现",
        "体会", "学到", "提升", "效率", "优缺点", "特点",
    ])
    return min(6, section_count), has_reflection


def analyze_student(student_dir_name, include_metrics=False):
    """整理单个学生作业素材，返回给 agent 阅读用的元数据。"""
    student_dir = os.path.join(EXTRACT_DIR, student_dir_name)
    if not os.path.isdir(student_dir):
        return None
    inspect_dir = prepare_student_dir(student_dir)

    parts = student_dir_name.split("-", 1)
    student_id = parts[0] if len(parts) > 0 else student_dir_name
    student_name = parts[1] if len(parts) > 1 else "未知"

    # 统一提取文字（自动处理 .docx 和 .doc）
    full_text, report_path, fmt = get_report_text(inspect_dir)
    img_count = count_report_images(inspect_dir, fmt, report_path) if report_path else 0

    result = {
        "student_id": student_id,
        "student_name": student_name,
        "dir_name": student_dir_name,
        "format": fmt,
        "char_count": len(full_text),
        "img_count": img_count,
        "report_path": report_path or "",
        "preview": preview_text(full_text),
    }
    if include_metrics:
        section_count, has_reflection = optional_metrics(full_text)
        result.update({
            "section_signal": section_count,
            "reflection_signal": has_reflection,
        })
    return result


def resolve_extract_dir(base_dir):
    """兼容常见解压结构：base_dir/docx_files、base_dir/extracted 或 base_dir 本身。"""
    for name in ("docx_files", "extracted"):
        candidate = os.path.join(base_dir, name)
        if os.path.isdir(candidate):
            return candidate
    return base_dir


def ensure_student_dirs(extract_dir):
    """If Chaoxing exported one zip per student, expand them into student folders."""
    for name in os.listdir(extract_dir):
        path = os.path.join(extract_dir, name)
        if not os.path.isfile(path) or not name.lower().endswith(".zip"):
            continue
        student_name = os.path.splitext(name)[0]
        target = os.path.join(extract_dir, student_name)
        os.makedirs(target, exist_ok=True)
        safe_extract_zip(path, target)


def parse_args():
    parser = argparse.ArgumentParser(description="批量整理 Chaoxing 作业附件，供 agent 逐份阅读评分。")
    parser.add_argument(
        "--base-dir",
        default=os.getcwd(),
        help="作业包解压目录；可直接指向含学生子目录的目录，或其上级目录。",
    )
    parser.add_argument(
        "--output-csv",
        default=None,
        help="CSV 输出路径；默认写入 base-dir/grading_materials.csv。",
    )
    parser.add_argument(
        "--mode",
        choices=("materials", "metrics"),
        default="materials",
        help="materials: 只整理素材，默认；metrics: 额外输出粗略指标信号，需用户明确选择。",
    )
    return parser.parse_args()


def main():
    global EXTRACT_DIR

    args = parse_args()
    base_dir = os.path.abspath(args.base_dir)
    include_metrics = args.mode == "metrics"
    default_name = "grading_metrics.csv" if include_metrics else "grading_materials.csv"
    output_csv = os.path.abspath(args.output_csv or os.path.join(base_dir, default_name))

    extract_dir = resolve_extract_dir(base_dir)
    if not os.path.isdir(extract_dir):
        print(f"ERROR: {extract_dir} not found. Unzip first.")
        return 1

    EXTRACT_DIR = extract_dir
    ensure_student_dirs(EXTRACT_DIR)

    results = []
    for d in sorted(os.listdir(extract_dir)):
        r = analyze_student(d, include_metrics=include_metrics)
        if r:
            results.append(r)

    # 打印汇总
    if include_metrics:
        print("MODE: metrics (粗略指标仅作辅助，不能替代 agent 逐份阅读)")
        print(f"{'学号':<12} {'姓名':<10} {'格式':<5} {'字符':>6} {'图片':>4} {'指标':>4} {'反思':>4}  报告文件")
    else:
        print("MODE: materials (默认，只整理素材)")
        print(f"{'学号':<12} {'姓名':<10} {'格式':<5} {'字符':>6} {'图片':>4}  报告文件")
    print("-" * 60)
    for r in sorted(results, key=lambda x: -x["char_count"]):
        if include_metrics:
            reflection = "yes" if r["reflection_signal"] else "no"
            print(
                f"{r['student_id']:<12} {r['student_name']:<10} {r['format']:<5} "
                f"{r['char_count']:>6} {r['img_count']:>4} {r['section_signal']:>4}/6 "
                f"{reflection:>4}  {r['report_path']}"
            )
        else:
            print(
                f"{r['student_id']:<12} {r['student_name']:<10} {r['format']:<5} "
                f"{r['char_count']:>6} {r['img_count']:>4}  {r['report_path']}"
            )

    print(f"\n共 {len(results)} 份作业")

    # 写 CSV
    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = [
            "student_id", "student_name", "dir_name", "format", "char_count",
            "img_count", "report_path", "preview"
        ]
        if include_metrics:
            fieldnames.extend(["section_signal", "reflection_signal"])
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"报告已保存: {output_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

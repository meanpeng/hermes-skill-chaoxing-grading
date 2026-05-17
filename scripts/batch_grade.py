#!/usr/bin/env python3
"""
批量分析 Chaoxing 作业的通用脚本框架。
用法：修改 BASE_DIR 和评分逻辑后运行。
输出：控制台汇总 + CSV 报告。

⚠️ 自动支持 .docx 和 .doc 格式，无需手动切换。
"""

import os
import csv
import struct

BASE_DIR = "/home/ubuntu/downloads/作业目录"
OUTPUT_CSV = os.path.join(BASE_DIR, "grading_report.csv")


def get_report_text(student_dir):
    """自动检测 .docx/.doc 并提取全部文字（段落 + 表格单元格）

    ⚠️ 超星实验报告模板使用表格布局，绝大部分内容在 table cells 里！
    只读 paragraphs 会得到 150-200 字的空表头。

    优先 .docx（python-docx 提取更完整），fallback 到 .doc（OLE2 解析）。
    返回 (text, file_path, format_type)。
    """
    from docx import Document
    import olefile

    files = os.listdir(student_dir)

    # 1) 优先找 .docx（排除模板文件）
    report_docxs = [f for f in files if f.endswith('.docx') and not any(
        kw in f for kw in ['V2024', '模板', 'template']
    )]
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
            if len(text) > 50:
                return text, path, 'docx'
        except Exception:
            pass

    # 2) Fallback: .doc (OLE2 格式)
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


def analyze_student(student_dir_name):
    """分析单个学生作业，返回分析结果字典"""
    student_dir = os.path.join(BASE_DIR, "docx_files", student_dir_name)
    if not os.path.isdir(student_dir):
        return None

    parts = student_dir_name.split("-", 1)
    student_id = parts[0] if len(parts) > 0 else student_dir_name
    student_name = parts[1] if len(parts) > 1 else "未知"

    # 统一提取文字（自动处理 .docx 和 .doc）
    full_text, report_path, fmt = get_report_text(student_dir)
    img_count = count_report_images(student_dir, fmt, report_path) if report_path else 0

    # 基础分析
    word_count = len(full_text)
    sections = ["一", "二", "三", "四", "五", "六"]
    section_count = sum(1 for s in sections if s + "、" in full_text)
    # 兜底：有些学生漏标序号但有内容，按关键词再检测
    section_keywords = {"五": ["实验步骤", "步骤与结果"], "六": ["实验总结", "本次实验总结"]}
    for sec, kws in section_keywords.items():
        if not (sec + "、" in full_text) and any(kw in full_text for kw in kws):
            section_count += 1

    # 检测总结质量
    summary_text = ""
    for line in full_text.split("\n"):
        if any(k in line for k in ["总结", "六、"]):
            idx = full_text.index(line)
            summary_text = full_text[idx:]
            break
    has_analysis = any(k in summary_text for k in [
        "对比", "分析", "差异", "认识", "理解", "掌握", "发现",
        "体会", "学到", "提升", "效率", "优缺点", "特点"
    ])

    return {
        "student_id": student_id,
        "student_name": student_name,
        "dir_name": student_dir_name,
        "format": fmt,
        "word_count": word_count,
        "img_count": img_count,
        "section_count": section_count,
        "has_analysis": has_analysis,
    }


def main():
    extract_dir = os.path.join(BASE_DIR, "docx_files")
    if not os.path.isdir(extract_dir):
        # fallback to "extracted" directory
        extract_dir = os.path.join(BASE_DIR, "extracted")
    if not os.path.isdir(extract_dir):
        print(f"ERROR: {extract_dir} not found. Unzip first.")
        return

    results = []
    for d in sorted(os.listdir(extract_dir)):
        r = analyze_student(d)
        if r:
            results.append(r)

    # 打印汇总
    print(f"{'学号':<12} {'姓名':<10} {'格式':<5} {'字数':>6} {'图片':>4} {'章节':>4} {'分析':>4}")
    print("-" * 60)
    for r in sorted(results, key=lambda x: -x["word_count"]):
        print(
            f"{r['student_id']:<12} {r['student_name']:<10} {r['format']:<5} "
            f"{r['word_count']:>6} {r['img_count']:>4} {r['section_count']:>4}/6 "
            f"{'✓' if r['has_analysis'] else '✗':>4}"
        )

    print(f"\n共 {len(results)} 份作业")

    # 写 CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "student_id", "student_name", "format", "word_count",
            "img_count", "section_count", "has_analysis"
        ])
        writer.writeheader()
        writer.writerows(results)
    print(f"报告已保存: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()

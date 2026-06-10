#!/usr/bin/env python3
"""Prepare Chaoxing exam Word exports for detailed grading review."""

import argparse
import base64
import csv
import html
import json
import re
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


FILENAME_RE = re.compile(r"-(?P<student_id>\d{6,})-(?P<student_name>[^-]+)-(?P<exam>[^.]+)\.doc$", re.I)
HEADER_RE = re.compile(
    r"答题人：\s*(?P<name>.*?)\s+学号：\s*(?P<student_id>\d+).*?"
    r"考试得分：\s*(?P<score>[0-9.]+)\s*分",
    re.S,
)
QUESTION_RE = re.compile(
    r"(?:^|\s)(?P<number>\d{1,2})\.\s*(?P<prompt>.*?)"
    r"学生得分：(?P<score>[0-9.]+)\s*分\s*"
    r"学生答案：\s*(?P<answer>.*?)(?=(?:正确答案：|评语：|批语：|得分点：|参考答案：|$))",
    re.S,
)
BASE64_IMAGE_RE = re.compile(r"(?P<data>/9j/[A-Za-z0-9+/=\s]+|iVBORw0KGgo[A-Za-z0-9+/=\s]+)")


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare Chaoxing exam .doc Word-HTML exports.")
    parser.add_argument("--input-dir", required=True, help="Directory containing exported .doc files.")
    parser.add_argument("--output-dir", required=True, help="Directory for parsed reports and extracted images.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    return parser.parse_args()


def read_word_html(path):
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def plain_text(markup):
    text = re.sub(r"<style[^>]*>.*?</style>", " ", markup, flags=re.S | re.I)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def filename_meta(path):
    match = FILENAME_RE.search(path.name)
    if not match:
        return {"student_id": "", "student_name": "", "exam": path.stem}
    return match.groupdict()


def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return re.sub(r"\s+", " ", name).strip(" .")[:160] or "item"


def decode_answer_images(answer, image_dir, prefix):
    paths = []
    for index, match in enumerate(BASE64_IMAGE_RE.finditer(answer), start=1):
        data = re.sub(r"\s+", "", match.group("data"))
        suffix = ".jpg" if data.startswith("/9j/") else ".png"
        try:
            payload = base64.b64decode(data, validate=False)
        except Exception:
            continue
        if len(payload) < 128:
            continue
        image_dir.mkdir(parents=True, exist_ok=True)
        path = image_dir / f"{prefix}-answer-{index}{suffix}"
        path.write_bytes(payload)
        paths.append(str(path.resolve()))
    return paths


def parse_exam_doc(path, output_dir):
    meta = filename_meta(path)
    markup = read_word_html(path)
    text = plain_text(markup)
    header = HEADER_RE.search(text)
    if header:
        meta["student_name"] = header.group("name").strip() or meta["student_name"]
        meta["student_id"] = header.group("student_id").strip() or meta["student_id"]
        total_score = header.group("score").strip()
    else:
        total_score = ""

    image_dir = output_dir / "images" / sanitize_filename(f"{meta['student_id']}-{meta['student_name']}")
    question_count = len(re.findall(r"学生得分：[0-9.]+\s*分", text))
    subjective = []
    review_text = text
    subjective_start = text.find("三 . 简答题")
    if subjective_start >= 0:
        review_text = text[subjective_start:]
    for match in QUESTION_RE.finditer(review_text):
        number = int(match.group("number"))
        prompt = match.group("prompt").strip()
        score = match.group("score").strip()
        answer = match.group("answer").strip()
        image_paths = decode_answer_images(answer, image_dir, f"q{number}")
        compact_answer = BASE64_IMAGE_RE.sub("[image-answer]", answer)
        compact_answer = re.sub(r"\s+", " ", compact_answer).strip()
        subjective.append(
            {
                "number": number,
                "prompt": prompt[:500],
                "score": score,
                "answer_preview": compact_answer[:500],
                "image_paths": image_paths,
            }
        )

    report_path = output_dir / "students" / f"{sanitize_filename(meta['student_id'] + '-' + meta['student_name'])}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_student_report(report_path, meta, total_score, question_count, subjective, path)

    return {
        "student_id": meta["student_id"],
        "student_name": meta["student_name"],
        "exam": meta["exam"],
        "total_score": total_score,
        "question_count": question_count,
        "subjective_count": len(subjective),
        "image_count": sum(len(item["image_paths"]) for item in subjective),
        "source_file": str(path.resolve()),
        "report_path": str(report_path.resolve()),
    }


def write_student_report(path, meta, total_score, question_count, subjective, source_file):
    with path.open("w", encoding="utf-8") as file:
        file.write(f"# {meta['student_id']} {meta['student_name']}\n\n")
        file.write(f"- exam: {meta['exam']}\n")
        file.write(f"- exported_score: {total_score}\n")
        file.write(f"- question_count: {question_count}\n")
        file.write(f"- source_file: {source_file.resolve()}\n\n")
        file.write("## Subjective / Review Items\n\n")
        if not subjective:
            file.write("No subjective review items detected.\n")
        for item in subjective:
            file.write(f"### Q{item['number']} | exported_score={item['score']}\n\n")
            file.write(f"Prompt: {item['prompt']}\n\n")
            file.write(f"Answer preview: {item['answer_preview']}\n\n")
            if item["image_paths"]:
                file.write("Images:\n")
                for image_path in item["image_paths"]:
                    file.write(f"- {image_path}\n")
                file.write("\n")


def write_csv(rows, path):
    fieldnames = [
        "student_id",
        "student_name",
        "exam",
        "total_score",
        "question_count",
        "subjective_count",
        "image_count",
        "source_file",
        "report_path",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_args()
    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    docs = sorted(input_dir.glob("*.doc"))
    if not docs:
        raise RuntimeError(f"no .doc files found in {input_dir}")

    rows = [parse_exam_doc(path, output_dir) for path in docs]
    csv_path = output_dir / "exam_materials.csv"
    json_path = output_dir / "exam_materials.json"
    write_csv(rows, csv_path)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "submission_count": len(rows),
        "csv": str(csv_path),
        "json": str(json_path),
        "image_count": sum(row["image_count"] for row in rows),
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"Prepared {summary['submission_count']} exam submissions; "
            f"images={summary['image_count']} csv={summary['csv']}"
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

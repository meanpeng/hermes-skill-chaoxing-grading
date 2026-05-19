#!/usr/bin/env python3
"""Batch extract downloaded Chaoxing work zips and prepare material/metric reports."""

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

import batch_grade
import extract_work_zip


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare downloaded Chaoxing work zip materials.")
    parser.add_argument("--zip-file", action="append", default=[], help="Downloaded work zip. Repeatable.")
    parser.add_argument("--zip-dir", help="Directory containing downloaded .zip files.")
    parser.add_argument("--output-dir", default="prepared-work-materials", help="Output directory.")
    parser.add_argument("--mode", choices=("materials", "metrics"), default="metrics")
    parser.add_argument("--min-chars", type=int, default=batch_grade.DEFAULT_MIN_CHARS)
    parser.add_argument("--sample", type=int, default=0, help="Print a representative sample per zip.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    return parser.parse_args()


def safe_name(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:160] or "work"


def collect_zip_files(args):
    paths = [Path(path) for path in args.zip_file]
    if args.zip_dir:
        paths.extend(sorted(Path(args.zip_dir).glob("*.zip")))
    seen = set()
    result = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if not resolved.is_file():
            raise FileNotFoundError(str(resolved))
        result.append(resolved)
    if not result:
        raise RuntimeError("pass --zip-file or --zip-dir")
    return result


def analyze_extracted_dir(base_dir, include_metrics, min_chars):
    extract_dir = batch_grade.resolve_extract_dir(str(base_dir))
    batch_grade.ensure_student_dirs(extract_dir)
    rows = []
    for name in sorted(os.listdir(extract_dir)):
        row = batch_grade.analyze_student(
            extract_dir,
            name,
            include_metrics=include_metrics,
            min_chars=min_chars,
        )
        if row:
            rows.append(row)
    return rows


def write_rows_csv(rows, output_csv, include_metrics):
    fieldnames = [
        "student_id",
        "student_name",
        "dir_name",
        "status",
        "format",
        "char_count",
        "img_count",
        "expanded_zip",
        "report_path",
        "preview",
    ]
    if include_metrics:
        fieldnames.extend(["section_signal", "key_requirement_signal"])
    with open(output_csv, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize_rows(rows):
    statuses = {}
    for row in rows:
        statuses[row["status"]] = statuses.get(row["status"], 0) + 1
    return {
        "submission_count": len(rows),
        "status_counts": dict(sorted(statuses.items())),
        "flagged_count": sum(
            1
            for row in rows
            if row["status"] in {"missing_report", "unreadable", "too_short"} or row["char_count"] == 0
        ),
    }


def process_zip(zip_path, output_root, include_metrics, min_chars, sample):
    work_dir = output_root / safe_name(zip_path.stem)
    extract_dir = work_dir / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)

    with extract_work_zip.open_zip(str(zip_path), "gbk") as zip_file:
        extract_work_zip.safe_extract(zip_file, str(extract_dir))

    rows = analyze_extracted_dir(extract_dir, include_metrics, min_chars)
    csv_name = "grading_metrics.csv" if include_metrics else "grading_materials.csv"
    output_csv = work_dir / csv_name
    write_rows_csv(rows, output_csv, include_metrics)
    report_md = work_dir / "agent_material_report.md"
    write_agent_report(rows, report_md, include_metrics, zip_path.name)

    display_rows = batch_grade.sample_results(sorted(rows, key=lambda row: row["student_id"]), sample)
    if sample:
        print(f"\n{zip_path.name}: showing {len(display_rows)} of {len(rows)} submissions")
        batch_grade.print_rows(display_rows, include_metrics=include_metrics)

    summary = summarize_rows(rows)
    return {
        "zip_file": str(zip_path),
        "work_dir": str(work_dir.resolve()),
        "extract_dir": str(extract_dir.resolve()),
        "csv": str(output_csv.resolve()),
        "agent_report": str(report_md.resolve()),
        **summary,
    }


def write_agent_report(rows, output_md, include_metrics, title):
    status_counts = summarize_rows(rows)["status_counts"]
    with open(output_md, "w", encoding="utf-8") as file:
        file.write(f"# Material Report: {title}\n\n")
        file.write("This report contains extraction and structure signals only. It does not contain draft scores, bands, or grading decisions.\n\n")
        file.write(f"- submissions: {len(rows)}\n")
        file.write("- status_counts: " + ", ".join(f"{key}={value}" for key, value in status_counts.items()) + "\n\n")
        headers = ["student_id", "student_name", "status", "format", "chars", "images"]
        if include_metrics:
            headers.extend(["sections", "key_requirements"])
        headers.append("report_path")
        file.write("| " + " | ".join(headers) + " |\n")
        file.write("| " + " | ".join("---" for _ in headers) + " |\n")
        for row in sorted(rows, key=lambda item: item["student_id"]):
            values = [
                row["student_id"],
                row["student_name"],
                row["status"],
                row["format"],
                str(row["char_count"]),
                str(row["img_count"]),
            ]
            if include_metrics:
                values.extend([
                    f"{row.get('section_signal', '')}/6",
                    "yes" if row.get("key_requirement_signal") else "no",
                ])
            values.append(row["report_path"])
            file.write("| " + " | ".join(escape_md(value) for value in values) + " |\n")


def escape_md(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_manifest(results, output_root):
    manifest_csv = output_root / "materials_manifest.csv"
    with open(manifest_csv, "w", newline="", encoding="utf-8-sig") as file:
        fieldnames = [
            "zip_file",
            "work_dir",
            "extract_dir",
            "csv",
            "agent_report",
            "submission_count",
            "flagged_count",
            "status_counts",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            row = dict(result)
            row["status_counts"] = json.dumps(row["status_counts"], ensure_ascii=False)
            writer.writerow(row)
    manifest_json = output_root / "materials_manifest.json"
    with open(manifest_json, "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
    return manifest_csv, manifest_json


def main():
    args = parse_args()
    output_root = Path(args.output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    include_metrics = args.mode == "metrics"

    results = [
        process_zip(path, output_root, include_metrics, args.min_chars, args.sample)
        for path in collect_zip_files(args)
    ]
    manifest_csv, manifest_json = write_manifest(results, output_root)

    if args.json:
        print(json.dumps({"results": results, "manifest_csv": str(manifest_csv), "manifest_json": str(manifest_json)}, ensure_ascii=False, indent=2))
    else:
        print(f"\nProcessed zip files: {len(results)}")
        for result in results:
            print(
                f"{Path(result['zip_file']).name}: submissions={result['submission_count']} "
                f"flagged={result['flagged_count']} csv={result['csv']} report={result['agent_report']}"
            )
        print(f"Manifest CSV: {manifest_csv}")
        print(f"Manifest JSON: {manifest_json}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

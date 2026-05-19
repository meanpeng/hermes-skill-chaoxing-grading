#!/usr/bin/env python3
"""Verify submitted Chaoxing scores by downloading the exported grade table."""

import argparse
import csv
import io
import json
import re
import sys
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from html import unescape

import chaoxing_discover
import submit_scores


MARK_PAGE_URL = "https://mooc2-ans.chaoxing.com/mooc2-ans/work/mark"
EXPORT_SCORE_URL = "https://mooc1.chaoxing.com/import-export-ans/export-workscore"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Download Chaoxing exported grades and verify target scores.")
    parser.add_argument("--cookie-file", default="cx_cookies.txt")
    parser.add_argument("--courseid", required=True)
    parser.add_argument("--clazzid", required=True)
    parser.add_argument("--cpi", required=True)
    parser.add_argument("--work-id", required=True)
    parser.add_argument("--scores-csv", required=True, help="CSV with expected student_id/name/score/workAnswerId.")
    parser.add_argument("--output-file", help="Optional path to keep the downloaded grade table.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def request(opener, url, data=None, referer=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    if referer:
        headers["Referer"] = referer
    if data:
        url += "?" + urllib.parse.urlencode(data)
    req = urllib.request.Request(url, headers=headers)
    with opener.open(req, timeout=60) as resp:
        return resp.read(), resp.geturl(), resp.headers


def get_export_enc(opener, args):
    params = {
        "courseid": args.courseid,
        "clazzid": args.clazzid,
        "id": args.work_id,
        "cpi": args.cpi,
        "evaluation": "0",
        "from": "",
        "v": "0",
        "prePageNum": "1",
        "prePageSize": "100",
        "topicid": "0",
    }
    body, final_url, _ = request(opener, MARK_PAGE_URL, params)
    html = body.decode("utf-8", errors="replace")
    enc = first_input_value(html, "workScoreExportEnc") or first_input_value(html, "enc")
    if not enc:
        raise RuntimeError(f"could not find export enc on mark page: {final_url}")
    return enc, final_url


def first_input_value(html, input_id):
    patterns = [
        rf'<input[^>]*(?:id|name)=["\']{re.escape(input_id)}["\'][^>]*value=["\']([^"\']*)',
        rf'<input[^>]*value=["\']([^"\']*)["\'][^>]*(?:id|name)=["\']{re.escape(input_id)}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.S)
        if match:
            return unescape(match.group(1))
    return ""


def download_export(opener, args, enc):
    params = {
        "courseId": args.courseid,
        "classId": args.clazzid,
        "workId": args.work_id,
        "mooc": "1",
        "isTemplate": "false",
        "cpi": args.cpi,
        "enc": enc,
        "addLog": "true",
    }
    body, final_url, headers = request(opener, EXPORT_SCORE_URL, params, referer=MARK_PAGE_URL)
    content_type = headers.get("Content-Type", "")
    if body[:2] != b"PK":
        preview = body[:300].decode("utf-8", errors="replace")
        raise RuntimeError(f"export did not return an OOXML workbook ({content_type}, {final_url}): {preview}")
    return body, final_url, content_type


def read_shared_strings(zf):
    try:
        xml = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(xml)
    strings = []
    for si in root.findall("m:si", NS):
        parts = [node.text or "" for node in si.findall(".//m:t", NS)]
        strings.append("".join(parts))
    return strings


def parse_workbook_rows(workbook_bytes):
    with zipfile.ZipFile(io.BytesIO(workbook_bytes)) as zf:
        shared = read_shared_strings(zf)
        sheet_name = first_sheet_name(zf)
        root = ET.fromstring(zf.read(sheet_name))
        rows = []
        for row in root.findall(".//m:sheetData/m:row", NS):
            values = {}
            for cell in row.findall("m:c", NS):
                ref = cell.attrib.get("r", "")
                col = re.sub(r"\d+", "", ref)
                values[col] = read_cell(cell, shared)
            if values:
                rows.append(values)
        return rows


def first_sheet_name(zf):
    names = [name for name in zf.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)]
    if not names:
        raise RuntimeError("workbook has no worksheet xml")
    return sorted(names)[0]


def read_cell(cell, shared):
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//m:t", NS)).strip()
    value = cell.find("m:v", NS)
    if value is None or value.text is None:
        return ""
    text = value.text
    if cell_type == "s":
        try:
            return shared[int(text)].strip()
        except (ValueError, IndexError):
            return text.strip()
    return text.strip()


def index_grade_rows(rows):
    indexed = {}
    for row in rows:
        student_id = normalize_id(row.get("A", ""))
        if not student_id or not re.search(r"\d", student_id):
            continue
        indexed[student_id] = {
            "student_id": student_id,
            "student_name": row.get("B", "").strip(),
            "score": normalize_score_text(row.get("I", "")),
            "status": row.get("J", "").strip(),
            "question_score": normalize_score_text(row.get("Q", "")),
        }
    return indexed


def normalize_id(value):
    text = str(value or "").strip()
    return text[:-2] if text.endswith(".0") else text


def normalize_score_text(value):
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    return submit_scores.format_score(number)


def verify(expected_rows, exported_rows):
    by_sid = index_grade_rows(exported_rows)
    results = []
    mismatches = []
    for expected in expected_rows:
        sid = normalize_id(expected["student_id"])
        target = normalize_score_text(expected["score"])
        exported = by_sid.get(sid)
        item = {
            "student_id": sid,
            "student_name": expected["student_name"],
            "expected_score": target,
            "exported_score": exported["score"] if exported else "",
            "exported_status": exported["status"] if exported else "",
            "match": bool(exported and exported["score"] == target),
        }
        if not item["match"]:
            mismatches.append(sid or expected["workAnswerId"] or f"line {expected['line_no']}")
        results.append(item)
    return results, mismatches


def output_result(result, as_json):
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print("verification_source: exported_grade_table")
    print(f"courseid={result['courseid']} clazzid={result['clazzid']} workId={result['workId']}")
    print(f"expected={result['expected_count']} verified={result['verified_count']} mismatches={len(result['mismatches'])}")
    print("student_id\tname\texpected\texported\tstatus\tmatch")
    for item in result["rows"]:
        print(
            f"{item['student_id']}\t{item['student_name']}\t{item['expected_score']}\t"
            f"{item['exported_score']}\t{item['exported_status']}\t{item['match']}"
        )
    if result["mismatches"]:
        print("Mismatches: " + ", ".join(result["mismatches"]))


def main():
    args = parse_args()
    opener = chaoxing_discover.make_opener(args.cookie_file)
    expected_rows = submit_scores.load_scores(args.scores_csv)
    enc, mark_url = get_export_enc(opener, args)
    workbook_bytes, export_url, content_type = download_export(opener, args, enc)
    if args.output_file:
        with open(args.output_file, "wb") as file:
            file.write(workbook_bytes)
    exported_rows = parse_workbook_rows(workbook_bytes)
    rows, mismatches = verify(expected_rows, exported_rows)
    result = {
        "courseid": args.courseid,
        "clazzid": args.clazzid,
        "cpi": args.cpi,
        "workId": args.work_id,
        "mark_url": mark_url,
        "export_url": export_url,
        "content_type": content_type,
        "output_file": args.output_file or "",
        "expected_count": len(expected_rows),
        "verified_count": sum(1 for row in rows if row["match"]),
        "mismatches": mismatches,
        "rows": rows,
    }
    output_result(result, args.json)
    return 0 if not mismatches else 1


if __name__ == "__main__":
    sys.exit(main())

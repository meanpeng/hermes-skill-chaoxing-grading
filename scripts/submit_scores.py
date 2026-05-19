#!/usr/bin/env python3
"""Dry-run-first score submission helper using Chaoxing's list-page API."""

import argparse
import csv
import json
import re
import sys
import urllib.parse
import urllib.request
from html import unescape

import chaoxing_discover


MARK_LIST_URL = "https://mooc2-ans.chaoxing.com/mooc2-ans/work/mark-list"
WORK_INFO_URL = "https://mooc2-ans.chaoxing.com/mooc2-ans/work/workinfo"
MARK_SCORE_URL = "https://mooc2-ans.chaoxing.com/mooc2-ans/work/markscore"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Validate or submit Chaoxing scores.")
    parser.add_argument("--cookie-file", default="cx_cookies.txt")
    parser.add_argument("--courseid", required=True)
    parser.add_argument("--clazzid", required=True)
    parser.add_argument("--cpi", required=True)
    parser.add_argument("--work-id", required=True)
    parser.add_argument("--scores-csv", required=True)
    parser.add_argument("--method", choices=("list-input",), default="list-input")
    parser.add_argument("--confirm-submit", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def request(opener, url, data=None, method="GET"):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }
    body = None
    if method == "GET" and data:
        url += "?" + urllib.parse.urlencode(data)
    elif data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with opener.open(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def get_work_info(opener, args):
    data = {
        "courseid": args.courseid,
        "clazzid": args.clazzid,
        "cpi": args.cpi,
        "workid": args.work_id,
    }
    body = request(opener, WORK_INFO_URL, data=data)
    parsed = json.loads(body)
    if not parsed.get("status"):
        raise RuntimeError(f"workinfo failed: {body[:300]}")
    return parsed["data"]


def get_mark_list(opener, args):
    data = {
        "courseid": args.courseid,
        "clazzid": args.clazzid,
        "cpi": args.cpi,
        "workid": args.work_id,
        "submit": "true",
        "evaluation": "0",
        "unEval": "false",
        "state": "0",
        "groupId": "0",
        "from": "",
        "ceyan": "0",
        "chapterid": "0",
        "workLibraryid": "",
        "prePageSize": "100",
        "prePageNum": "1",
        "noBack": "false",
        "topicid": "0",
        "backurl": "",
        "attachmentWorkId": "",
        "sort": "0",
        "order": "0",
        "status": "0",
        "pageNum": "1",
        "pageSize": "100",
    }
    html = request(opener, MARK_LIST_URL, data=data)
    rows = []
    for chunk in re.findall(r'(<ul class="dataBody_td" id="\d+".*?</ul>)', html, re.S):
        answer_id = first_match(chunk, r'<ul class="dataBody_td" id="(\d+)"')
        person_id = first_match(chunk, r'createid="(\d+)"')
        name = clean(first_match(chunk, r'<div class="py_name"[^>]*>(.*?)</div>'))
        values = [clean(value) for value in re.findall(r'<li class="taskBody_con[^"]*">(.*?)</li>', chunk, re.S)]
        student_id = values[0] if values else ""
        status = values[3] if len(values) > 3 else ""
        score = first_match(chunk, r'<input class="inp80 scoreInput"[^>]*value="([^"]*)"')
        rows.append(
            {
                "student_id": student_id,
                "student_name": name,
                "person_id": person_id,
                "workAnswerId": answer_id,
                "status": status,
                "current_score": score,
            }
        )
    return rows


def first_match(text, pattern):
    match = re.search(pattern, text, re.S)
    return unescape(match.group(1)) if match else ""


def clean(text):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def load_scores(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for line_no, row in enumerate(reader, start=2):
            student_id = value(row, "student_id", "sid", "学号")
            student_name = value(row, "student_name", "name", "姓名")
            score = value(row, "score", "分数", "建议分")
            work_answer_id = value(row, "workAnswerId", "work_answer_id", "answer_id", "wid")
            if not student_id and not student_name and not score and not work_answer_id:
                continue
            rows.append(
                {
                    "line_no": line_no,
                    "student_id": student_id,
                    "student_name": student_name,
                    "score": score,
                    "workAnswerId": work_answer_id,
                }
            )
    return rows


def value(row, *names):
    for name in names:
        item = row.get(name)
        if item is not None and str(item).strip():
            return str(item).strip()
    return ""


def normalize_score(score):
    try:
        parsed = float(score)
    except (TypeError, ValueError):
        raise ValueError(f"invalid score {score!r}")
    if parsed < 0:
        raise ValueError(f"score below 0: {parsed:g}")
    return parsed


def build_plan(score_rows, mark_rows, full_score):
    by_sid = {row["student_id"]: row for row in mark_rows if row["student_id"]}
    by_answer = {row["workAnswerId"]: row for row in mark_rows if row["workAnswerId"]}
    plan = []
    errors = []
    seen = set()
    for row in score_rows:
        label = f"line {row['line_no']}"
        key = row["workAnswerId"] or row["student_id"]
        if not key:
            errors.append(f"{label}: missing student_id or workAnswerId")
            continue
        if key in seen:
            errors.append(f"{label}: duplicate target {key}")
            continue
        seen.add(key)
        try:
            score = normalize_score(row["score"])
        except ValueError as exc:
            errors.append(f"{label}: {exc}")
            continue
        if score > full_score:
            errors.append(f"{label}: score {score:g} exceeds full score {full_score:g}")
            continue
        mark = by_answer.get(row["workAnswerId"]) if row["workAnswerId"] else by_sid.get(row["student_id"])
        if not mark:
            errors.append(f"{label}: no submitted mark-list row matched")
            continue
        if row["student_id"] and mark["student_id"] and row["student_id"] != mark["student_id"]:
            errors.append(f"{label}: student_id mismatch for workAnswerId {mark['workAnswerId']}")
            continue
        if row["student_name"] and mark["student_name"] and row["student_name"] != mark["student_name"]:
            errors.append(f"{label}: student_name mismatch for {mark['student_id']}: {row['student_name']} != {mark['student_name']}")
            continue
        plan.append({**mark, "score": score})
    return plan, errors


def submit_markscore(opener, args, item):
    query = {
        "markScore": format_score(item["score"]),
        "markAnswerIds": item["workAnswerId"],
        "markType": "0",
    }
    data = {
        "courseid": args.courseid,
        "clazzid": args.clazzid,
        "cpi": args.cpi,
        "workid": args.work_id,
        "answerIds": item["workAnswerId"],
        "type": "0",
        "score": format_score(item["score"]),
    }
    url = MARK_SCORE_URL + "?" + urllib.parse.urlencode(query)
    body = request(opener, url, data=data, method="POST")
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return {"ok": False, "body": body[:300]}
    return {"ok": bool(parsed.get("status")), "body": parsed}


def format_score(score):
    text = f"{score:.1f}"
    return text[:-2] if text.endswith(".0") else text


def output_result(result, as_json):
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"method: {result['method']} | dry_run={result['dry_run']}")
    print(f"courseid={result['courseid']} clazzid={result['clazzid']} workId={result['workId']}")
    print(
        f"full_score={result['full_score']:g} submitted={result['submitted']} "
        f"unsubmitted={result['unsubmitted']} targets={len(result['plan'])}"
    )
    if result["errors"]:
        print("Errors:")
        for error in result["errors"]:
            print(f"- {error}")
    print("student_id\tname\tanswerId\tcurrent\ttarget")
    for item in result["plan"]:
        print(
            f"{item['student_id']}\t{item['student_name']}\t{item['workAnswerId']}\t"
            f"{item['current_score']}\t{format_score(item['score'])}"
        )
    if result["dry_run"]:
        print("\nDRY RUN: no scores were written. Add --confirm-submit only after user confirms this exact list.")
    elif result.get("submit_results"):
        print("Submit results:")
        for submit_result in result["submit_results"]:
            print(submit_result)


def main():
    args = parse_args()
    opener = chaoxing_discover.make_opener(args.cookie_file)
    info = get_work_info(opener, args)
    mark_rows = get_mark_list(opener, args)
    score_rows = load_scores(args.scores_csv)
    plan, errors = build_plan(score_rows, mark_rows, float(info["score"]))
    result = {
        "method": args.method,
        "dry_run": not args.confirm_submit,
        "courseid": args.courseid,
        "clazzid": args.clazzid,
        "cpi": args.cpi,
        "workId": args.work_id,
        "full_score": float(info["score"]),
        "submitted": int(info["submitCount"]),
        "unsubmitted": int(info["noSubmitCount"]),
        "plan": plan,
        "errors": errors,
    }
    if errors:
        output_result(result, args.json)
        return 1
    if not args.confirm_submit:
        output_result(result, args.json)
        return 0
    submit_results = []
    for item in plan:
        submit_results.append({"student_id": item["student_id"], "workAnswerId": item["workAnswerId"], **submit_markscore(opener, args, item)})
    result["submit_results"] = submit_results
    output_result(result, args.json)
    return 0 if all(item["ok"] for item in submit_results) else 1


if __name__ == "__main__":
    sys.exit(main())

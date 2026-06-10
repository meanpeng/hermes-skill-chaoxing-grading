#!/usr/bin/env python3
"""Dry-run-first score submission helper for Chaoxing exam mark lists."""

import argparse
import csv
import json
import re
import sys
import urllib.parse
import urllib.request

import chaoxing_discover


MARK_RESULT_URL = "https://mooc2-ans.chaoxing.com/mooc2-ans/exam/test/markresult-new"
BATCH_MARK_SCORE_URL = "https://mooc2-ans.chaoxing.com/mooc2-ans/exam/test/batch-markscore"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Validate or submit Chaoxing exam scores.")
    parser.add_argument("--cookie-file", default="cx_cookies.txt")
    parser.add_argument("--courseid", required=True)
    parser.add_argument("--clazzid", required=True)
    parser.add_argument("--cpi", required=True)
    parser.add_argument("--relationid", required=True, help="Exam relation id from the marklist URL or clazzAndRelationId.")
    parser.add_argument("--scores-csv", required=True)
    parser.add_argument("--full-score", type=float, default=100.0)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--confirm-submit", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def request(opener, url, data=None, method="GET"):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": (
            "https://mooc2-ans.chaoxing.com/mooc2-ans/exam/test/marklist?"
            + urllib.parse.urlencode(
                {
                    "clazzid": data.get("clazzid", "") if data else "",
                    "courseid": data.get("courseid", "") if data else "",
                    "cpi": data.get("cpi", "") if data else "",
                    "id": data.get("id", "") if data else "",
                }
            )
        ),
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


def mark_result_params(args, page_num):
    return {
        "courseid": args.courseid,
        "clazzid": args.clazzid,
        "cpi": args.cpi,
        "ut": "",
        "id": args.relationid,
        "sw": "",
        "schoolId": "-1",
        "schoolName": "",
        "sort": "",
        "sorttype": "",
        "state": "1",
        "status": "-1",
        "groupIds": "",
        "groupid": "-1",
        "reviewMarkLabel": "0",
        "markType": "0",
        "hideInvigilation": "0",
        "hideRetest": "false",
        "updateScore": "1",
        "allowAnnotationRedoDownload": "1",
        "pages": str(page_num),
        "size": str(args.page_size),
    }


def get_mark_rows(opener, args):
    rows = []
    seen = set()
    total = None
    page_num = 1
    while True:
        body = request(opener, MARK_RESULT_URL, data=mark_result_params(args, page_num), method="POST")
        parsed = json.loads(body)
        if total is None:
            total = int(parsed.get("total") or 0)
        page_rows = parsed.get("data") or []
        for row in page_rows:
            answer_id = str(row.get("id") or "").strip()
            if not answer_id or answer_id in seen:
                continue
            seen.add(answer_id)
            rows.append(
                {
                    "answer_id": answer_id,
                    "student_id": str(row.get("loginName") or "").strip(),
                    "student_name": str(row.get("createUserName") or "").strip(),
                    "status": str(row.get("mark") or "").strip(),
                    "current_score": row.get("answerScore"),
                    "can_update": bool(row.get("tchPiYueExam")),
                }
            )
        if total and len(rows) >= total:
            break
        if not page_rows:
            break
        page_num += 1
    return rows


def load_scores(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for line_no, row in enumerate(reader, start=2):
            student_id = value(row, "student_id", "sid", "学号")
            student_name = value(row, "student_name", "name", "姓名")
            answer_id = value(row, "answer_id", "examAnswerId", "exam_answer_id")
            score = value(row, "score", "draft_total", "total", "总分", "建议分")
            if not student_id and not student_name and not answer_id and not score:
                continue
            rows.append(
                {
                    "line_no": line_no,
                    "student_id": student_id,
                    "student_name": student_name,
                    "answer_id": answer_id,
                    "score": score,
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
    by_answer = {row["answer_id"]: row for row in mark_rows if row["answer_id"]}
    plan = []
    errors = []
    seen = set()
    for row in score_rows:
        label = f"line {row['line_no']}"
        target_key = row["answer_id"] or row["student_id"]
        if not target_key:
            errors.append(f"{label}: missing student_id or answer_id")
            continue
        if target_key in seen:
            errors.append(f"{label}: duplicate target {target_key}")
            continue
        seen.add(target_key)
        try:
            score = normalize_score(row["score"])
        except ValueError as exc:
            errors.append(f"{label}: {exc}")
            continue
        if score > full_score:
            errors.append(f"{label}: score {score:g} exceeds full score {full_score:g}")
            continue
        mark = by_answer.get(row["answer_id"]) if row["answer_id"] else by_sid.get(row["student_id"])
        if not mark:
            errors.append(f"{label}: no submitted exam row matched")
            continue
        if row["student_id"] and mark["student_id"] and row["student_id"] != mark["student_id"]:
            errors.append(f"{label}: student_id mismatch for answer_id {mark['answer_id']}")
            continue
        if row["student_name"] and mark["student_name"] and row["student_name"] != mark["student_name"]:
            errors.append(
                f"{label}: student_name mismatch for {mark['student_id']}: "
                f"{row['student_name']} != {mark['student_name']}"
            )
            continue
        if not mark["can_update"]:
            errors.append(f"{label}: exam row is not editable for {mark['student_id']} {mark['student_name']}")
            continue
        plan.append({**mark, "score": score})
    return plan, errors


def submit_exam_score(opener, args, item):
    data = {
        "courseid": args.courseid,
        "clazzid": args.clazzid,
        "cpi": args.cpi,
        "ut": "",
        "relationid": args.relationid,
        "answerids": item["answer_id"],
        "score": format_score(item["score"]),
        "way": "singlesum",
    }
    body = request(opener, BATCH_MARK_SCORE_URL, data=data, method="POST")
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return {"ok": False, "raw": body[:500]}
    return {"ok": bool(parsed.get("status")), "response": parsed}


def format_score(score):
    if abs(score - round(score)) < 0.0000001:
        return str(int(round(score)))
    return f"{score:.1f}".rstrip("0").rstrip(".")


def main():
    args = parse_args()
    opener = chaoxing_discover.make_opener(args.cookie_file)
    mark_rows = get_mark_rows(opener, args)
    score_rows = load_scores(args.scores_csv)
    plan, errors = build_plan(score_rows, mark_rows, args.full_score)

    output = {
        "mode": "submit" if args.confirm_submit else "dry-run",
        "remote_rows": len(mark_rows),
        "score_rows": len(score_rows),
        "planned": len(plan),
        "errors": errors,
        "plan": [
            {
                "student_id": item["student_id"],
                "student_name": item["student_name"],
                "answer_id": item["answer_id"],
                "current_score": item["current_score"],
                "score": format_score(item["score"]),
                "status": item["status"],
            }
            for item in plan
        ],
    }
    if errors:
        print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else "\n".join(errors))
        return 2

    if not args.confirm_submit:
        if args.json:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(f"Dry run only. Remote rows={len(mark_rows)}, planned submissions={len(plan)}")
            for item in output["plan"]:
                print(
                    f"{item['student_id']} {item['student_name']} "
                    f"answer_id={item['answer_id']} {item['current_score']} -> {item['score']}"
                )
            print("Pass --confirm-submit only after reviewing the exact plan.")
        return 0

    results = []
    for item in plan:
        result = submit_exam_score(opener, args, item)
        results.append({**item, **result})
        if not result["ok"]:
            break
    output["results"] = results
    output["submitted"] = sum(1 for item in results if item.get("ok"))
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"Submitted {output['submitted']} of {len(plan)} exam scores")
        for item in results:
            status = "ok" if item.get("ok") else "failed"
            print(f"{status}: {item['student_id']} {item['student_name']} -> {format_score(item['score'])}")
    return 0 if output["submitted"] == len(plan) else 1


if __name__ == "__main__":
    raise SystemExit(main())

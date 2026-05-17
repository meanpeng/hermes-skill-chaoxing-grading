#!/usr/bin/env python3
"""
Dry-run-first batch score submission helper for Chaoxing/Xuexitong.

Run it locally to validate a CSV. Execute in a browser-harness style Python
environment only after the teacher explicitly confirms final scores.
"""

import argparse
import csv
import json
import os
import sys
import time


# Legacy fallback values. Prefer CLI arguments and --scores-csv.
COURSEID = ""
CLAZZID = ""
CPI = ""
WORK_ID = ""
SCORES = {}
WORK_ANSWER_IDS = {}


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def parse_args():
    parser = argparse.ArgumentParser(description="Preview or submit Chaoxing scores.")
    parser.add_argument("--courseid", default=COURSEID, help="Chaoxing courseid.")
    parser.add_argument("--clazzid", default=CLAZZID, help="Chaoxing clazzid/current class id.")
    parser.add_argument("--cpi", default=CPI, help="Chaoxing cpi. Optional for many review URLs.")
    parser.add_argument("--work-id", default=WORK_ID, help="Chaoxing workId.")
    parser.add_argument(
        "--scores-csv",
        default=None,
        help="CSV with student_id, score, and workAnswerId/work_answer_id columns.",
    )
    parser.add_argument(
        "--confirm-submit",
        action="store_true",
        help="Actually navigate, fill scores, and call markAction(1). Omit for dry-run.",
    )
    return parser.parse_args()


def load_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for line_no, row in enumerate(reader, start=2):
            sid = first_value(row, "student_id", "sid", "学号")
            score = first_value(row, "score", "分数", "建议分")
            wid = first_value(row, "workAnswerId", "work_answer_id", "wid")
            if not sid and not score and not wid:
                continue
            rows.append({"sid": sid, "score": score, "wid": wid, "line_no": line_no})
    return rows


def first_value(row, *names):
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def load_legacy_scores():
    rows = []
    for sid, score in SCORES.items():
        rows.append({"sid": str(sid), "score": score, "wid": WORK_ANSWER_IDS.get(sid, ""), "line_no": None})
    return rows


def normalize_todo(rows):
    todo, errors = [], []
    for row in rows:
        label = f"line {row['line_no']}" if row.get("line_no") else row.get("sid", "legacy row")
        sid = str(row.get("sid") or "").strip()
        wid = str(row.get("wid") or "").strip()
        if not sid:
            errors.append(f"{label}: missing student_id")
            continue
        if not wid:
            errors.append(f"{sid}: missing workAnswerId")
            continue
        try:
            score = float(row.get("score"))
        except (TypeError, ValueError):
            errors.append(f"{sid}: score is not numeric: {row.get('score')!r}")
            continue
        if not 0 <= score <= 100:
            errors.append(f"{sid}: score out of 0-100 range: {score:g}")
            continue
        todo.append({"sid": sid, "score": score, "wid": wid})
    return todo, errors


def require_browser_submit_environment():
    if "cdp" not in globals() or "js" not in globals():
        return (
            "submit mode requires a browser automation Python environment "
            "providing cdp(...) and js(...). Run without --confirm-submit for dry-run."
        )
    return None


def review_url(courseid, clazzid, work_id, wid):
    return (
        "https://mooc2-ans.chaoxing.com/mooc2-ans/work/library/review-work"
        f"?courseid={courseid}&clazzid={clazzid}&workId={work_id}"
        f"&workAnswerId={wid}&groupId=0&from=&sort=0&order=0&status=0"
        "&pages=1&size=20&topicid=0"
    )


def print_plan(args, todo):
    print("=== Pending score list ===")
    for student in todo:
        print(f"{student['sid']}: {student['score']:g} (workAnswerId={student['wid']})")

    missing_url = [
        name for name, value in {
            "courseid": args.courseid,
            "clazzid": args.clazzid,
            "work-id": args.work_id,
        }.items()
        if not str(value).strip()
    ]
    if missing_url:
        print("\nURL fields missing: " + ", ".join(missing_url))
        print("Dry-run is still useful for validating scores, but submit mode needs these fields.")
    else:
        print("\nFirst review URL preview:")
        print(review_url(args.courseid, args.clazzid, args.work_id, todo[0]["wid"]))


def submit_scores(args, todo):
    env_error = require_browser_submit_environment()
    if env_error:
        return fail(env_error)

    missing_url = [
        name for name, value in {
            "courseid": args.courseid,
            "clazzid": args.clazzid,
            "work-id": args.work_id,
        }.items()
        if not str(value).strip()
    ]
    if missing_url:
        return fail("submit mode is missing URL fields: " + ", ".join(missing_url))

    results = []
    for index, student in enumerate(todo, start=1):
        url = review_url(args.courseid, args.clazzid, args.work_id, student["wid"])
        cdp("Page.navigate", url=url)
        time.sleep(3)

        score_json = json.dumps(student["score"])
        js(f"""
            var qInput = document.querySelector('input.questionScore');
            if (qInput) {{
                qInput.value = String({score_json});
                $(qInput).trigger('input').trigger('change').trigger('keyup').trigger('blur');
            }}
            $('#tmpscore').val(String({score_json}));
            $('#score').val(String({score_json}));
        """)
        time.sleep(1)

        js("markAction(1)")
        time.sleep(3)

        results.append(f"{student['sid']}: {student['score']:g} submitted")
        if index % 5 == 0:
            print(f"Progress: {index}/{len(todo)}")

    print("\n=== Done ===")
    for result in results:
        print(result)
    return 0


def main():
    args = parse_args()
    if args.scores_csv:
        if not os.path.isfile(args.scores_csv):
            return fail(f"scores CSV not found: {args.scores_csv}")
        rows = load_csv(args.scores_csv)
    else:
        rows = load_legacy_scores()

    if not rows:
        print("No scores found.")
        print("Example CSV columns: student_id,score,workAnswerId")
        print("Dry-run example:")
        print("  python scripts/batch_submit_scores.py --courseid 123 --clazzid 456 --work-id 789 --scores-csv scores.csv")
        return 1

    todo, errors = normalize_todo(rows)
    if errors:
        print("Validation errors:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    if not todo:
        return fail("no valid score rows")

    print_plan(args, todo)
    if not args.confirm_submit:
        print("\nDRY RUN: no navigation, score filling, or submission was performed.")
        print("Only rerun with --confirm-submit after the teacher explicitly confirms the final list.")
        return 0

    print("\nCONFIRMED SUBMIT MODE: writing scores to Chaoxing.")
    return submit_scores(args, todo)


if __name__ == "__main__":
    sys.exit(main())

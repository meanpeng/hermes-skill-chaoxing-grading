#!/usr/bin/env python3
"""Dry-run-first export/download helper for Chaoxing exam zip packages."""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

import chaoxing_discover


DOWNLOAD_CENTER_URL = "https://mooc2-ans.chaoxing.com/mooc2-ans/tcm/downloadcenter"
PACK_EXAM_URL = "https://mooc2-ans.chaoxing.com/mooc2-ans/exam/test/packexam"
CHECK_DOWNLOAD_RECORD_URL = "https://mooc2-ans.chaoxing.com/mooc2-ans/tcm/check-download-record"

FORMAT_PARAMS = {
    "word": {"onlyattachment": "0", "label": "word"},
    "attachment": {"onlyattachment": "1", "label": "attachment"},
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Package and download Chaoxing exam zips.")
    parser.add_argument("--cookie-file", default="cx_cookies.txt", help="MozillaCookieJar cookie file.")
    parser.add_argument("--course", help="Course name keyword or exact course name.")
    parser.add_argument("--class-contains", default="", help="Only include classes whose name contains this text.")
    parser.add_argument("--exam-contains", default="", help="Only include exams whose title contains this text.")
    parser.add_argument("--relationid", action="append", default=[], help="Only include this exam relation id. Repeatable.")
    parser.add_argument("--paper-id", help="Paper id for direct single-target mode.")
    parser.add_argument("--clazzid", help="Class id for direct single-target mode.")
    parser.add_argument("--courseid", help="Skip course search and use this courseid.")
    parser.add_argument("--cpi", help="Skip course search and use this cpi.")
    parser.add_argument("--base-clazzid", help="Course shell clazzid. Auto-detected when omitted.")
    parser.add_argument("--discover-json", help="Read targets from a previous chaoxing_discover.py --json output.")
    parser.add_argument("--format", choices=sorted(FORMAT_PARAMS), default="word", help="Export package format.")
    parser.add_argument("--output-dir", default="downloads/chaoxing-exam-zips", help="Directory for downloaded zip files.")
    parser.add_argument("--poll-interval", type=float, default=5.0, help="Seconds between download-center checks.")
    parser.add_argument("--timeout", type=float, default=180.0, help="Seconds to wait for each packaged zip.")
    parser.add_argument("--force-pack", action="store_true", help="Trigger a new package even if an existing zip is found.")
    parser.add_argument("--confirm-download", action="store_true", help="Actually package/download. Omit for dry-run.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    return parser.parse_args()


def load_discovery(args, opener):
    if args.discover_json:
        with open(args.discover_json, encoding="utf-8") as file:
            return json.load(file)
    if args.courseid and args.cpi:
        course = {"course": args.course or "", "courseid": args.courseid, "cpi": args.cpi}
        return chaoxing_discover.discover_course_detail(opener, course, args.class_contains, args.base_clazzid)
    courses = chaoxing_discover.discover_courses(opener, args.course)
    course = chaoxing_discover.select_course(courses, args.course)
    return chaoxing_discover.discover_course_detail(opener, course, args.class_contains, args.base_clazzid)


def select_targets(discovery, args):
    direct = direct_target(discovery, args)
    if direct:
        return [direct]

    wanted_ids = set(str(relationid) for relationid in args.relationid)
    targets = []
    for cls in discovery.get("classes", []):
        for exam in cls.get("exams", []):
            relationid = str(exam.get("relationid", ""))
            title = exam.get("exam", "")
            if wanted_ids and relationid not in wanted_ids:
                continue
            if args.exam_contains and args.exam_contains not in title:
                continue
            targets.append(
                {
                    "course": discovery.get("course", ""),
                    "courseid": discovery["courseid"],
                    "cpi": discovery["cpi"],
                    "clazzid": cls["clazzid"],
                    "class": cls["class"],
                    "exam": title,
                    "relationid": relationid,
                    "paperId": str(exam.get("paperId", "")),
                    "submitted": exam.get("submitted", 0),
                    "pending_review": exam.get("pending_review", 0),
                    "unsubmitted": exam.get("unsubmitted", 0),
                    "mark_url": exam.get("mark_url", ""),
                }
            )
    return targets


def direct_target(discovery, args):
    if not (args.courseid and args.cpi and args.clazzid and args.relationid and args.paper_id):
        return None
    if len(args.relationid) != 1:
        raise RuntimeError("direct single-target mode requires exactly one --relationid")
    return {
        "course": discovery.get("course", args.course or ""),
        "courseid": args.courseid,
        "cpi": args.cpi,
        "clazzid": args.clazzid,
        "class": args.class_contains or args.clazzid,
        "exam": args.exam_contains or args.relationid[0],
        "relationid": args.relationid[0],
        "paperId": args.paper_id,
        "submitted": "",
        "pending_review": "",
        "unsubmitted": "",
        "mark_url": "",
    }


def fetch(opener, url, data=None, method="GET", referer=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    if referer:
        headers["Referer"] = referer
    body = None
    if data is not None and method == "GET":
        url = f"{url}?{urllib.parse.urlencode(data)}"
    elif data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with opener.open(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace"), resp.geturl()


def package_exam(opener, target, package_format):
    data = {
        "courseid": target["courseid"],
        "clazzid": target["clazzid"],
        "relationid": target["relationid"],
        "personIds": "",
        "cpi": target["cpi"],
        "type": "1",
        "packtype": "1",
        "isMoudle": "false",
        "onlyattachment": FORMAT_PARAMS[package_format]["onlyattachment"],
        "isGroupExport": "0",
        "iswatermark": "0",
        "taskId": "",
        "fileform": "0",
        "signatureType": "0",
    }
    body, url = fetch(opener, PACK_EXAM_URL, data=data, method="GET", referer=target.get("mark_url") or "")
    return {"url": url, "body": body[:1000]}


def get_download_center(opener, courseid, cpi):
    data = {"courseId": courseid, "pageNum": "1", "cpi": cpi, "order": "down"}
    body, _ = fetch(opener, DOWNLOAD_CENTER_URL, data=data)
    return body


def parse_download_entries(html):
    entries = []
    chunks = re.findall(r'(<ul class="dataBody_td"[^>]*>.*?</ul>)', html, re.S)
    for chunk in chunks:
        title = clean(first_match(chunk, r'<li title="([^"]*)"')) or clean(
            first_match(chunk, r'<span class="nameText">(.+?)</span>')
        )
        status = clean(first_match(chunk, r'<li class="exporting"[^>]*>(.*?)</li>'))
        href = unescape(first_match(chunk, r'href="(https://fanyadata\.chaoxing\.com/testzip/[^"]+)"'))
        record_id = first_match(chunk, r'recordid="(\d+)"') or first_match(chunk, r'<ul[^>]*data="(\d+)"')
        raw_data = first_match(chunk, r"data='([^']+)'")
        data = parse_attr_json(raw_data)
        entry = {
            "title": title,
            "status": status,
            "href": href,
            "recordId": record_id,
            "clazzid": str(data.get("clazzId", "")),
            "paperId": str(data.get("libraryId", "")),
            "relationid": str(data.get("relationId", "")),
            "check_safe": "checkSafe" in chunk,
        }
        if href:
            parsed = urllib.parse.urlparse(href)
            query = urllib.parse.parse_qs(parsed.query)
            entry["filename"] = urllib.parse.unquote(query.get("fn", [""])[0])
            path_match = re.search(r"/testzip/([^/]+)/([^/]+)/([^/]+)/[^/]+/([^/]+)/([^/?]+)", parsed.path)
            if path_match:
                _, courseid, clazzid, package_format, zip_name = path_match.groups()
                entry.update(
                    {
                        "courseid": courseid,
                        "clazzid": clazzid,
                        "format": package_format,
                        "zip_name": zip_name,
                        "relationid": (re.search(r"_(\d+)\.zip$", zip_name) or [None, entry["relationid"]])[1],
                    }
                )
        entries.append(entry)
    return entries


def parse_attr_json(raw):
    if not raw:
        return {}
    try:
        return json.loads(unescape(raw))
    except json.JSONDecodeError:
        return {}


def check_download_record(opener, target, entry):
    data = {
        "courseid": target["courseid"],
        "recordId": entry["recordId"],
        "relationId": target["relationid"],
        "clazzId": target["clazzid"],
        "paperid": target["paperId"],
    }
    body, _ = fetch(opener, CHECK_DOWNLOAD_RECORD_URL, data=data, method="GET")
    parsed = json.loads(body)
    if not parsed.get("status"):
        raise RuntimeError(f"check-download-record failed: {body[:300]}")
    return parsed.get("downloadUrl", "")


def first_match(text, pattern):
    match = re.search(pattern, text, re.S)
    return unescape(match.group(1)) if match else ""


def clean(text):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def find_download_entry(entries, target, package_format):
    label = FORMAT_PARAMS[package_format]["label"]
    for entry in entries:
        if entry.get("clazzid") and entry.get("clazzid") != str(target["clazzid"]):
            continue
        if entry.get("relationid") and entry.get("relationid") != str(target["relationid"]):
            continue
        if entry.get("paperId") and target.get("paperId") and entry.get("paperId") != str(target["paperId"]):
            continue
        if entry.get("href") and entry.get("format") != label:
            continue
        if not entry.get("href") and f"({label})" not in entry.get("title", ""):
            continue
        return entry
    return None


def safe_filename(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:180] or "download.zip"


def target_path(output_dir, target, package_format):
    name = f"{target['class']}-{target['exam']}({package_format})-{target['relationid']}.zip"
    return Path(output_dir) / safe_filename(name)


def download_file(opener, url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with opener.open(req, timeout=180) as resp, open(path, "wb") as file:
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            file.write(chunk)
    return path.stat().st_size


def wait_for_entry(opener, target, package_format, timeout, poll_interval):
    deadline = time.time() + timeout
    while True:
        html = get_download_center(opener, target["courseid"], target["cpi"])
        entry = find_download_entry(parse_download_entries(html), target, package_format)
        if entry:
            return entry
        if time.time() >= deadline:
            return None
        time.sleep(poll_interval)


def resolve_download_url(opener, target, entry):
    if entry.get("href"):
        return entry["href"]
    if entry.get("check_safe") and entry.get("recordId"):
        return check_download_record(opener, target, entry)
    return ""


def print_dry_run(targets, package_format, output_dir):
    print("DRY RUN: no packaging or downloading performed. Add --confirm-download to run.")
    print(f"format: {package_format} | output_dir: {output_dir}")
    print("clazzid\trelationid\tpaperId\tsubmitted\tpending\tunsubmitted\tclass\texam")
    for target in targets:
        print(
            f"{target['clazzid']}\t{target['relationid']}\t{target['paperId']}\t{target['submitted']}\t"
            f"{target['pending_review']}\t{target['unsubmitted']}\t{target['class']}\t{target['exam']}"
        )


def main():
    args = parse_args()
    opener = chaoxing_discover.make_opener(args.cookie_file)
    discovery = load_discovery(args, opener)
    targets = select_targets(discovery, args)
    if not targets:
        raise RuntimeError("no matching exams found")

    if not args.confirm_download:
        if args.json:
            print(json.dumps({"dry_run": True, "format": args.format, "targets": targets}, ensure_ascii=False, indent=2))
        else:
            print_dry_run(targets, args.format, args.output_dir)
        return 0

    results = []
    for target in targets:
        path = target_path(args.output_dir, target, args.format)
        existing_entry = None
        if not args.force_pack:
            existing_entry = find_download_entry(
                parse_download_entries(get_download_center(opener, target["courseid"], target["cpi"])),
                target,
                args.format,
            )
        entry = existing_entry
        pack_result = None
        if entry is None:
            pack_result = package_exam(opener, target, args.format)
            entry = wait_for_entry(opener, target, args.format, args.timeout, args.poll_interval)
        if entry is None:
            results.append({"target": target, "status": "timeout", "path": str(path), "pack_result": pack_result})
            continue
        download_url = resolve_download_url(opener, target, entry)
        if not download_url:
            results.append({"target": target, "status": "missing_download_url", "path": str(path), "download_entry": entry})
            continue
        size = download_file(opener, download_url, path)
        results.append(
            {
                "target": target,
                "status": "downloaded",
                "path": str(path),
                "bytes": size,
                "reused_existing_package": existing_entry is not None,
                "download_entry": entry,
            }
        )

    if args.json:
        print(json.dumps({"dry_run": False, "format": args.format, "results": results}, ensure_ascii=False, indent=2))
    else:
        for result in results:
            target = result["target"]
            print(
                f"{result['status']}: {target['class']} | {target['exam']} | "
                f"relationid={target['relationid']} | {result.get('bytes', 0)} bytes | {result['path']}"
            )
    return 0 if all(result["status"] == "downloaded" for result in results) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

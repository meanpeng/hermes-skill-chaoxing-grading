#!/usr/bin/env python3
"""Dry-run-first batch export/download helper for Chaoxing assignment zip packages."""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

import chaoxing_discover


DOWNLOAD_CENTER_URL = "https://mooc2-ans.chaoxing.com/mooc2-ans/tcm/downloadcenter"
PACK_WORK_URL = "https://mooc2-ans.chaoxing.com/mooc2-ans/work/packWork"

FORMAT_PARAMS = {
    "word": {"onlyattachment": "0", "isPdf": "0", "label": "word"},
    "pdf": {"onlyattachment": "1", "isPdf": "1", "label": "pdf"},
    "attachment": {"onlyattachment": "1", "isPdf": "0", "label": "attachment"},
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Package and download Chaoxing assignment zips.")
    parser.add_argument("--cookie-file", default="cx_cookies.txt", help="MozillaCookieJar cookie file.")
    parser.add_argument("--course", help="Course name keyword or exact course name.")
    parser.add_argument("--class-contains", default="", help="Only include classes whose name contains this text.")
    parser.add_argument("--assignment-contains", default="", help="Only include assignments whose title contains this text.")
    parser.add_argument("--work-id", action="append", default=[], help="Only include this workId. Repeatable.")
    parser.add_argument("--courseid", help="Skip course search and use this courseid.")
    parser.add_argument("--cpi", help="Skip course search and use this cpi.")
    parser.add_argument("--base-clazzid", help="Course shell clazzid. Auto-detected when omitted.")
    parser.add_argument("--discover-json", help="Read targets from a previous chaoxing_discover.py --json output.")
    parser.add_argument("--format", choices=sorted(FORMAT_PARAMS), default="word", help="Export package format.")
    parser.add_argument("--output-dir", default="downloads/chaoxing-work-zips", help="Directory for downloaded zip files.")
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
    else:
        course = chaoxing_discover.select_course(
            chaoxing_discover.discover_courses(opener, args.course),
            args.course,
        )

    base_clazzid = args.base_clazzid
    entry_url = ""
    if not base_clazzid:
        base_clazzid, entry_course_name, entry_url = chaoxing_discover.get_base_clazzid(
            opener, course["courseid"], course["cpi"]
        )
        if not course["course"] and entry_course_name:
            course["course"] = entry_course_name
    if not base_clazzid:
        raise RuntimeError("could not detect base clazzid; pass --base-clazzid")

    all_html, work_list_url = chaoxing_discover.discover_work_for_class(
        opener, course["courseid"], base_clazzid, course["cpi"], "0"
    )
    classes = chaoxing_discover.parse_classes(all_html, args.class_contains)
    for cls in classes:
        html, url = chaoxing_discover.discover_work_for_class(
            opener, course["courseid"], base_clazzid, course["cpi"], cls["clazzid"]
        )
        cls["page_url"] = url
        cls["assignments"] = chaoxing_discover.parse_assignments(html)

    return {
        "course": course["course"],
        "courseid": course["courseid"],
        "cpi": course["cpi"],
        "base_clazzid": base_clazzid,
        "course_entry_url": entry_url,
        "work_list_url": work_list_url,
        "class_filter": args.class_contains,
        "classes": classes,
    }


def select_targets(discovery, assignment_contains, work_ids):
    wanted_ids = set(str(work_id) for work_id in work_ids)
    targets = []
    for cls in discovery.get("classes", []):
        for assignment in cls.get("assignments", []):
            work_id = str(assignment.get("workId", ""))
            title = assignment.get("assignment", "")
            if wanted_ids and work_id not in wanted_ids:
                continue
            if assignment_contains and assignment_contains not in title:
                continue
            targets.append(
                {
                    "course": discovery.get("course", ""),
                    "courseid": discovery["courseid"],
                    "cpi": discovery["cpi"],
                    "clazzid": cls["clazzid"],
                    "class": cls["class"],
                    "assignment": title,
                    "workId": work_id,
                    "submitted": assignment.get("submitted", 0),
                    "pending_review": assignment.get("pending_review", 0),
                    "unsubmitted": assignment.get("unsubmitted", 0),
                }
            )
    return targets


def post_or_get(opener, url, data=None, referer=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    if referer:
        headers["Referer"] = referer
    body = None
    if data is not None:
        url = f"{url}?{urllib.parse.urlencode(data)}"
    req = urllib.request.Request(url, data=body, headers=headers)
    with opener.open(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace"), resp.geturl()


def package_work(opener, target, package_format):
    fmt = FORMAT_PARAMS[package_format]
    data = {
        "courseid": target["courseid"],
        "clazzid": target["clazzid"],
        "workid": target["workId"],
        "type": "0",
        "onlyattachment": fmt["onlyattachment"],
        "isPdf": fmt["isPdf"],
        "packtype": "1",
        "customNameGroup": "",
        "wordCustomFormat": "",
        "personIds": "",
    }
    body, url = post_or_get(opener, PACK_WORK_URL, data=data, referer=target.get("mark_url") or "")
    return {"url": url, "body": body[:1000]}


def get_download_center(opener, courseid, cpi):
    url = f"{DOWNLOAD_CENTER_URL}?{urllib.parse.urlencode({'courseId': courseid, 'pageNum': '1', 'cpi': cpi, 'order': 'down'})}"
    body, _ = post_or_get(opener, url)
    return body


def parse_download_entries(html):
    entries = []
    chunks = re.findall(r'(<ul class="dataBody_td"[^>]*>.*?</ul>)', html, re.S)
    for chunk in chunks:
        title = clean(first_match(chunk, r'<li title="([^"]*)"')) or clean(
            first_match(chunk, r'<span class="nameText">(.+?)</span>')
        )
        href = unescape(first_match(chunk, r'href="(https://fanyadata\.chaoxing\.com/workzip/[^"]+)"'))
        if not href:
            continue
        parsed = urllib.parse.urlparse(href)
        query = urllib.parse.parse_qs(parsed.query)
        filename = urllib.parse.unquote(query.get("fn", [""])[0])
        path_match = re.search(r"/workzip/([^/]+)/([^/]+)/([^/]+)/[^/]+/([^/]+)/([^/?]+)", parsed.path)
        fid = courseid = clazzid = package_format = zip_name = ""
        work_id = ""
        if path_match:
            fid, courseid, clazzid, package_format, zip_name = path_match.groups()
            work_id = (re.search(r"_(\d+)\.zip$", zip_name) or [None, ""])[1]
        entries.append(
            {
                "title": title,
                "href": href,
                "filename": filename or zip_name,
                "fid": fid,
                "courseid": courseid,
                "clazzid": clazzid,
                "format": package_format,
                "workId": work_id,
            }
        )
    return entries


def first_match(text, pattern):
    match = re.search(pattern, text, re.S)
    return unescape(match.group(1)) if match else ""


def clean(text):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def find_download_entry(entries, target, package_format):
    for entry in entries:
        if entry.get("courseid") != str(target["courseid"]):
            continue
        if entry.get("clazzid") != str(target["clazzid"]):
            continue
        if entry.get("workId") != str(target["workId"]):
            continue
        if entry.get("format") != FORMAT_PARAMS[package_format]["label"]:
            continue
        return entry
    return None


def safe_filename(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:180] or "download.zip"


def target_path(output_dir, target, package_format):
    name = f"{target['class']}-{target['assignment']}({package_format})-{target['workId']}.zip"
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


def print_dry_run(targets, package_format, output_dir):
    print("DRY RUN: no packaging or downloading performed. Add --confirm-download to run.")
    print(f"format: {package_format} | output_dir: {output_dir}")
    print("clazzid\tworkId\tsubmitted\tpending\tunsubmitted\tclass\tassignment")
    for target in targets:
        print(
            f"{target['clazzid']}\t{target['workId']}\t{target['submitted']}\t"
            f"{target['pending_review']}\t{target['unsubmitted']}\t{target['class']}\t{target['assignment']}"
        )


def main():
    args = parse_args()
    opener = chaoxing_discover.make_opener(args.cookie_file)
    discovery = load_discovery(args, opener)
    targets = select_targets(discovery, args.assignment_contains, args.work_id)
    if not targets:
        raise RuntimeError("no matching assignments found")

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
            pack_result = package_work(opener, target, args.format)
            entry = wait_for_entry(opener, target, args.format, args.timeout, args.poll_interval)
        if entry is None:
            results.append({"target": target, "status": "timeout", "path": str(path), "pack_result": pack_result})
            continue
        size = download_file(opener, entry["href"], path)
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
                f"{result['status']}: {target['class']} | {target['assignment']} | "
                f"workId={target['workId']} | {result.get('bytes', 0)} bytes | {result['path']}"
            )
    return 0 if all(result["status"] == "downloaded" for result in results) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

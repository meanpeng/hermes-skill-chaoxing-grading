#!/usr/bin/env python3
"""
Export final-grade aggregate data from Chaoxing/Xuexitong.

Triggers the "one-click export" on the 学情统计 page and downloads an Excel file
containing 作业统计, 考试统计 and 签到详情统计 for a single class.
"""

import argparse
import html
import http.cookiejar
import re
import sys
import time
import urllib.parse
import urllib.request


TEACH_DATA_EXPORT_URL = "https://stat2-ans.chaoxing.com/teach-data/export"
DOWNLOAD_CENTER_LIST_URL = "https://mooc2-ans.chaoxing.com/mooc2-ans/tcm/downloadcenter"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export Chaoxing final-grade aggregate data (homework, exam, attendance)."
    )
    parser.add_argument("--courseid", required=True, help="Course ID.")
    parser.add_argument("--clazzid", required=True, help="Class ID.")
    parser.add_argument("--cpi", required=True, help="Current person ID (cpi).")
    parser.add_argument(
        "--cookie-file",
        default="cx_cookies.txt",
        help="MozillaCookieJar cookie file. Default: cx_cookies.txt",
    )
    parser.add_argument(
        "--output",
        default="all.xlsx",
        help="Output file path. Default: all.xlsx",
    )
    parser.add_argument(
        "--tables",
        default="7,8,12",
        help="Comma-separated table IDs to export. Default: 7,8,12 (homework, exam, attendance).",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=3,
        help="Seconds between download-center polls. Default: 3",
    )
    parser.add_argument(
        "--poll-max",
        type=int,
        default=20,
        help="Maximum poll attempts. Default: 20",
    )
    return parser.parse_args()


def make_opener(cookie_file):
    jar = http.cookiejar.MozillaCookieJar(cookie_file)
    jar.load(ignore_discard=True, ignore_expires=True)
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def fetch(opener, url, data=None, referer=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    if referer:
        headers["Referer"] = referer
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    req = urllib.request.Request(url, data=body, headers=headers)
    with opener.open(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def trigger_export(opener, courseid, clazzid, cpi, tables):
    """Call /teach-data/export to enqueue the aggregate export task."""
    params = {
        "courseid": courseid,
        "clazzid": clazzid,
        "seltables": tables,
        "cpi": cpi,
        "ut": "t",
        "type": "1",        # current class only
        "exportType": "2",  # one-click data export
        "fr": "stat2",
    }
    url = f"{TEACH_DATA_EXPORT_URL}?{urllib.parse.urlencode(params)}"
    referer = (
        f"https://stat2-ans.chaoxing.com/teach-data/index?"
        f"courseid={courseid}&clazzid={clazzid}&cpi={cpi}&ut=t&sv=2"
    )
    body = fetch(opener, url, referer=referer)
    if body.strip() != '{"status":true}':
        print(f"WARNING: unexpected export response: {body}", file=sys.stderr)
    return body


def list_download_center(opener, courseid, cpi):
    """Fetch the download center HTML and parse export rows."""
    params = {
        "courseId": courseid,
        "pageNum": "1",
        "cpi": cpi,
        "order": "down",
    }
    url = f"{DOWNLOAD_CENTER_LIST_URL}?{urllib.parse.urlencode(params)}"
    html_text = fetch(opener, url)

    rows = []
    for m in re.finditer(
        r'<ul[^>]*data="(\d+)"[^>]*data-status="(\d)".*?</ul>', html_text, re.S
    ):
        row_html = m.group(0)
        name_match = re.search(r'class="nameText"[^>]*>([^<]+)', row_html)
        link_match = re.search(r'href="(https?://[^"]+)"', row_html)
        rows.append(
            {
                "id": m.group(1),
                "status": m.group(2),
                "name": html.unescape(name_match.group(1)) if name_match else "",
                "link": html.unescape(link_match.group(1)) if link_match else "",
            }
        )
    return rows


def find_fystat_export(rows, courseid, clazzid, tables):
    """Return the first fystat-ans export row matching the requested tables."""
    wanted = set(tables.split(","))
    for row in rows:
        if "fystat-ans.chaoxing.com/api/export" not in row["link"]:
            continue
        qs = urllib.parse.urlparse(row["link"]).query
        params = urllib.parse.parse_qs(qs)
        if params.get("courseId", [None])[0] != courseid:
            continue
        if params.get("classId", [None])[0] != clazzid:
            continue
        if set(params.get("seltables", [])) == wanted:
            return row
    return None


def download_file(opener, url, output_path):
    """Download the export file to disk."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with opener.open(req, timeout=60) as resp:
        data = resp.read()
    with open(output_path, "wb") as f:
        f.write(data)
    return len(data)


def main():
    args = parse_args()
    opener = make_opener(args.cookie_file)

    print(f"Triggering export for course={args.courseid} class={args.clazzid} tables={args.tables}")
    trigger_export(opener, args.courseid, args.clazzid, args.cpi, args.tables)

    print("Polling download center...")
    matched = None
    for attempt in range(1, args.poll_max + 1):
        time.sleep(args.poll_interval)
        rows = list_download_center(opener, args.courseid, args.cpi)
        matched = find_fystat_export(rows, args.courseid, args.clazzid, args.tables)
        if matched:
            print(f"Found export task {matched['id']} ({matched['name']}) on attempt {attempt}")
            break
        print(f"  attempt {attempt}/{args.poll_max}: not ready yet")
    else:
        print("ERROR: export did not appear in download center.", file=sys.stderr)
        return 1

    if matched["status"] != "1":
        print(f"Waiting for task {matched['id']} to finish...")
        for attempt in range(1, args.poll_max + 1):
            time.sleep(args.poll_interval)
            rows = list_download_center(opener, args.courseid, args.cpi)
            for row in rows:
                if row["id"] == matched["id"]:
                    matched = row
                    break
            if matched["status"] == "1":
                print(f"Task finished on attempt {attempt}")
                break
            print(f"  attempt {attempt}/{args.poll_max}: status={matched['status']}")
        else:
            print("ERROR: export did not finish in time.", file=sys.stderr)
            return 1

    print(f"Downloading to {args.output}")
    size = download_file(opener, matched["link"], args.output)
    print(f"Saved {size} bytes to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

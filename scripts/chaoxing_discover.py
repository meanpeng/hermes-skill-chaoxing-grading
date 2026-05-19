#!/usr/bin/env python3
"""Read-only Chaoxing course/class/assignment discovery from saved cookies."""

import argparse
import http.cookiejar
import json
import re
import sys
import urllib.parse
import urllib.request
from html import unescape


COURSE_LIST_URL = "https://mooc2-ans.chaoxing.com/mooc2-ans/visit/courselistdata"
COURSE_ENTRY_URL = "https://mooc1.chaoxing.com/course/isNewCourse"
WORK_LIST_URL = "https://mooc2-ans.chaoxing.com/mooc2-ans/work/list"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Discover teacher courses, classes, and assignments.")
    parser.add_argument("--cookie-file", default="cx_cookies.txt", help="MozillaCookieJar cookie file.")
    parser.add_argument("--course", help="Course name keyword or exact course name.")
    parser.add_argument("--class-contains", default="", help="Only include classes whose name contains this text.")
    parser.add_argument("--courseid", help="Skip course search and use this courseid.")
    parser.add_argument("--cpi", help="Skip course search and use this cpi.")
    parser.add_argument("--base-clazzid", help="Course shell clazzid from course entry page. Auto-detected when omitted.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a readable table.")
    return parser.parse_args()


def clean(text):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


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
        return resp.read().decode("utf-8", errors="replace"), resp.geturl()


def discover_courses(opener, query):
    data = {
        "courseType": "0",
        "courseFolderId": "0",
        "query": query or "",
        "pageHeader": "-1",
        "single": "0",
        "superstarClass": "0",
        "isFirefly": "0",
    }
    html, _ = fetch(opener, COURSE_LIST_URL, data=data, referer="https://mooc2-ans.chaoxing.com/visit/interaction")
    chunks = re.findall(r'(<div class="course clearfix\s+teachCourse".*?</div>\s*</div>\s*</div>)', html, re.S)
    courses = []
    for chunk in chunks:
        courseid = first_match(chunk, r'class="courseId"[^>]*value="(\d+)"')
        cpi = first_match(chunk, r'class="curPersonId"[^>]*value="(\d+)"')
        name = first_match(chunk, r'<span class="course-name[^"]*"[^>]*title="([^"]*)"')
        if courseid and cpi:
            courses.append({"course": clean(name), "courseid": courseid, "cpi": cpi})
    return courses


def first_match(text, pattern):
    match = re.search(pattern, text, re.S)
    return unescape(match.group(1)) if match else ""


def get_base_clazzid(opener, courseid, cpi):
    url = f"{COURSE_ENTRY_URL}?{urllib.parse.urlencode({'courseId': courseid, 'edit': 'true', 'v': '2', 'cpi': cpi, 'pageHeader': '-1', 'single': '0'})}"
    html, final_url = fetch(opener, url)
    clazzid = first_match(html, r'id="clazzid"[^>]*value="(\d+)"')
    course_name = clean(first_match(html, r'<dd class="textHidden[^"]*"[^>]*title="([^"]*)"'))
    return clazzid, course_name, final_url


def parse_classes(html, class_contains):
    classes = []
    for clazzid, title in re.findall(r'<li[^>]*class="[^"]*classli[^"]*"[^>]*data="(\d+)"[^>]*title="([^"]*)"', html, re.S):
        name = clean(title)
        if clazzid == "0":
            continue
        if class_contains and class_contains not in name:
            continue
        classes.append({"clazzid": clazzid, "class": name})
    return classes


def parse_assignments(html):
    assignments = []
    chunks = re.findall(r'(<li id="work\d+".*?</li>)', html, re.S)
    for chunk in chunks:
        work_id = first_match(chunk, r'<li id="work(\d+)"')
        title = clean(first_match(chunk, r'<h2[^>]*>(.*?)</h2>'))
        class_name = clean(first_match(chunk, r'<div class="list_class[^"]*"[^>]*title="([^"]*)"'))
        pending = first_match(chunk, r'<em[^>]*>(\d+)</em>\s*待批')
        submitted = first_match(chunk, r'<span>(\d+)\s*已交</span>')
        unsubmitted = first_match(chunk, r'<span>(\d+)\s*未交</span>')
        mark_url = unescape(first_match(chunk, r'href="([^"]*/mooc2-ans/work/mark[^"]+)"'))
        if mark_url.startswith("/"):
            mark_url = "https://mooc2-ans.chaoxing.com" + mark_url
        assignments.append(
            {
                "assignment": title,
                "workId": work_id,
                "class": class_name,
                "pending_review": int(pending or 0),
                "submitted": int(submitted or 0),
                "unsubmitted": int(unsubmitted or 0),
                "mark_url": mark_url,
            }
        )
    return assignments


def discover_work_for_class(opener, courseid, base_clazzid, cpi, clazzid):
    params = {
        "courseid": courseid,
        "clazzid": base_clazzid,
        "selectClassid": clazzid,
        "cpi": cpi,
        "status": "-1",
        "v": "0",
        "topicid": "0",
        "pages": "1",
        "size": "100",
    }
    url = f"{WORK_LIST_URL}?{urllib.parse.urlencode(params)}"
    html, final_url = fetch(opener, url)
    return html, final_url


def select_course(courses, requested):
    if not courses:
        raise RuntimeError("no teacher courses found")
    if not requested:
        if len(courses) == 1:
            return courses[0]
        raise RuntimeError("multiple courses found; pass --course")
    exact = [course for course in courses if course["course"] == requested]
    if len(exact) == 1:
        return exact[0]
    contains = [course for course in courses if requested in course["course"]]
    if len(contains) == 1:
        return contains[0]
    if not contains:
        raise RuntimeError(f"no course matched {requested!r}")
    names = ", ".join(course["course"] for course in contains)
    raise RuntimeError(f"multiple courses matched {requested!r}: {names}")


def discover_course_detail(opener, course, class_contains, base_clazzid=None):
    entry_course_name = ""
    entry_url = ""
    if not base_clazzid:
        base_clazzid, entry_course_name, entry_url = get_base_clazzid(opener, course["courseid"], course["cpi"])
    if not base_clazzid:
        raise RuntimeError(f"could not detect base clazzid for {course['course']}; pass --base-clazzid")
    if not course["course"] and entry_course_name:
        course["course"] = entry_course_name

    all_html, work_list_url = discover_work_for_class(opener, course["courseid"], base_clazzid, course["cpi"], "0")
    classes = parse_classes(all_html, class_contains)
    for cls in classes:
        html, url = discover_work_for_class(opener, course["courseid"], base_clazzid, course["cpi"], cls["clazzid"])
        cls["page_url"] = url
        cls["assignments"] = parse_assignments(html)

    return {
        "course": course["course"],
        "courseid": course["courseid"],
        "cpi": course["cpi"],
        "base_clazzid": base_clazzid,
        "course_entry_url": entry_url,
        "work_list_url": work_list_url,
        "class_filter": class_contains,
        "classes": classes,
    }


def build_discovery(opener, args):
    if args.courseid and args.cpi:
        course = {"course": args.course or "", "courseid": args.courseid, "cpi": args.cpi}
        return discover_course_detail(opener, course, args.class_contains, args.base_clazzid)

    courses = discover_courses(opener, args.course)
    if not courses:
        raise RuntimeError("no teacher courses found")

    if not args.course and len(courses) > 1:
        if not args.class_contains:
            return {
                "mode": "course-list",
                "message": "multiple courses found; pass --course, or add --class-contains to scan matching classes across courses",
                "courses": courses,
            }
        scanned = [discover_course_detail(opener, dict(course), args.class_contains) for course in courses]
        matched = [course for course in scanned if course["classes"]]
        return {
            "mode": "multi-course-class-scan",
            "class_filter": args.class_contains,
            "courses": matched,
            "scanned_course_count": len(scanned),
            "matched_course_count": len(matched),
        }

    course = select_course(courses, args.course)
    return discover_course_detail(opener, course, args.class_contains, args.base_clazzid)


def print_table(result):
    if result.get("mode") == "course-list":
        print(result["message"])
        print("courseid\tcpi\tcourse")
        for course in result["courses"]:
            print(f"{course['courseid']}\t{course['cpi']}\t{course['course']}")
        return
    if result.get("mode") == "multi-course-class-scan":
        print(
            f"class_filter: {result['class_filter']} | "
            f"matched_courses={result['matched_course_count']} | scanned_courses={result['scanned_course_count']}"
        )
        for course in result["courses"]:
            print()
            print_table(course)
        return
    print(f"course: {result['course']} | courseid={result['courseid']} | cpi={result['cpi']}")
    print(f"base_clazzid: {result['base_clazzid']}")
    for cls in result["classes"]:
        print(f"\nclass: {cls['class']} | clazzid={cls['clazzid']} | assignments={len(cls['assignments'])}")
        print("workId\tpending\tsubmitted\tunsubmitted\tassignment")
        for item in cls["assignments"]:
            print(
                f"{item['workId']}\t{item['pending_review']}\t{item['submitted']}\t"
                f"{item['unsubmitted']}\t{item['assignment']}"
            )


def main():
    args = parse_args()
    opener = make_opener(args.cookie_file)
    result = build_discovery(opener, args)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_table(result)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

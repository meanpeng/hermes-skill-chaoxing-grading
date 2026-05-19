#!/usr/bin/env python3
"""Check whether a Chaoxing MozillaCookieJar cookie file still reaches i.chaoxing.com."""

import argparse
import http.cookiejar
import json
import sys
import urllib.error
import urllib.request


CHECK_URL = "https://i.chaoxing.com"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Check a Chaoxing cookie file.")
    parser.add_argument("--cookie-file", default="cx_cookies.txt", help="MozillaCookieJar cookie file.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def check_cookie(cookie_file):
    jar = http.cookiejar.MozillaCookieJar(cookie_file)
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except FileNotFoundError:
        return {"valid": False, "status": None, "url": CHECK_URL, "reason": "cookie file not found"}
    except Exception as exc:
        return {"valid": False, "status": None, "url": CHECK_URL, "reason": f"cannot load cookie file: {exc}"}

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    req = urllib.request.Request(
        CHECK_URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )

    try:
        with opener.open(req, timeout=30) as resp:
            status = resp.getcode()
            url = resp.geturl()
            body = resp.read(200_000).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return {"valid": False, "status": exc.code, "url": exc.geturl(), "reason": str(exc)}
    except Exception as exc:
        return {"valid": False, "status": None, "url": CHECK_URL, "reason": str(exc)}

    login_markers = ("passport2.chaoxing.com", "用户登录", "账号登录", "login")
    space_markers = ("个人空间", "账号：", "课程")
    valid = status == 200 and any(marker in body for marker in space_markers) and not any(
        marker in url for marker in login_markers
    )
    reason = "ok" if valid else "cookie did not reach personal space"
    return {"valid": valid, "status": status, "url": url, "cookie_count": len(jar), "reason": reason}


def main():
    args = parse_args()
    result = check_cookie(args.cookie_file)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        state = "valid" if result["valid"] else "invalid"
        print(f"{state}: status={result.get('status')} url={result.get('url')} reason={result.get('reason')}")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())

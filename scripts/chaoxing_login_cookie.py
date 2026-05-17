#!/usr/bin/env python3
"""
Login to Chaoxing/Xuexitong and save cookies in MozillaCookieJar format.

This script is intentionally cross-platform: it uses only Python stdlib plus
pycryptodome, so it works from PowerShell, cmd, Bash, zsh, or CI shells.
"""

import argparse
import base64
import getpass
import http.cookiejar
import sys
import urllib.parse
import urllib.request


AES_KEY = b"u2oh6Vu^HWe4_AES"
LOGIN_URL = "https://passport2.chaoxing.com/fanyalogin"


def encrypt(text):
    try:
        from Crypto.Cipher import AES
    except ImportError:
        print("ERROR: missing dependency pycryptodome. Run: python -m pip install -r requirements.txt", file=sys.stderr)
        raise SystemExit(1)

    text_bytes = text.encode("utf-8")
    pad_len = 16 - (len(text_bytes) % 16)
    padded = text_bytes + bytes([pad_len] * pad_len)
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY)
    return base64.b64encode(cipher.encrypt(padded)).decode("ascii")


def parse_args():
    parser = argparse.ArgumentParser(description="Login to Chaoxing and save cookies.")
    parser.add_argument("--phone", required=True, help="Chaoxing login phone/account.")
    parser.add_argument(
        "--cookie-file",
        default="cx_cookies.txt",
        help="Output cookie file path. Default: cx_cookies.txt",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Password. Omit this option to enter it interactively without echo.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    password = args.password or getpass.getpass("Chaoxing password: ")

    data = urllib.parse.urlencode({
        "fid": "-1",
        "uname": encrypt(args.phone),
        "password": encrypt(password),
        "refer": "https://i.chaoxing.com",
        "t": "true",
        "doubleFactorLogin": "0",
        "forbidotherlogin": "0",
        "independentId": "0",
        "independentNameId": "0",
    }).encode("utf-8")

    req = urllib.request.Request(
        LOGIN_URL,
        data=data,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://passport2.chaoxing.com",
        },
    )

    cookie_jar = http.cookiejar.MozillaCookieJar(args.cookie_file)
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    with opener.open(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", errors="replace")

    if '"status":true' not in body.replace(" ", "").lower():
        print(body)
        print("ERROR: login did not report success.", file=sys.stderr)
        return 1

    cookie_jar.save(ignore_discard=True, ignore_expires=True)
    print(f"Saved {len(cookie_jar)} cookies to {args.cookie_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

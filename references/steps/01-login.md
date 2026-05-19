# Step 01: Login

Read `references/agent-rules.md` first. This file only explains login mechanics.

## Cookie Check

Before logging in again, check whether an existing cookie file still reaches personal space:

```bash
python scripts/check_cookie.py --cookie-file cx_cookies.txt
```

For machine-readable output:

```bash
python scripts/check_cookie.py --cookie-file cx_cookies.txt --json
```

Legacy curl fallback:

```bash
curl -s -b cx_cookies.txt "https://i.chaoxing.com" -o /dev/null -w "%{http_code}"
```

Treat script `valid: true` as valid. For the legacy curl fallback, treat `200` as likely valid and `302` as expired. Do not assume either state without checking when a cookie file exists.

## Login Script

If login is needed:

```bash
python scripts/chaoxing_login_cookie.py --phone "188xxxx1234" --cookie-file cx_cookies.txt
```

Omit `--password` when possible so the password is entered without echo. Do not repeat the password in logs or reports.

## Browser Cookie Injection

For browser automation, inject saved cookies through CDP rather than `document.cookie`; `vc3` and `p_auth_token` are httpOnly.

```python
ensure_real_tab()
cdp("Network.enable")
# Load cx_cookies.txt with MozillaCookieJar, then call Network.setCookie for each cookie.
cdp("Page.navigate", url="https://i.chaoxing.com")
```

If a browser helper reports `Unknown Target method: activateTarget`, reuse the current real tab and navigate with `Page.navigate`.

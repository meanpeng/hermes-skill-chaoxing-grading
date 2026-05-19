# Step 01: Login

Read `references/agent-rules.md` first. This file only explains login mechanics.

## Cookie Check

Before logging in again, use the skill directory as the working directory and check the cookie file at the relative path `./cx_cookies.txt`. This path works from Bash, zsh, and Windows PowerShell when commands are run from the skill directory. If a previous run saved cookies elsewhere, copy or move that file back to `./cx_cookies.txt` instead of continuing with an environment-specific absolute path.

Then use the skill-local relative path:

```bash
python scripts/check_cookie.py --cookie-file ./cx_cookies.txt
```

For machine-readable output:

```bash
python scripts/check_cookie.py --cookie-file ./cx_cookies.txt --json
```

Legacy curl fallback for Bash/zsh or real `curl.exe` on Windows:

```bash
curl -s -b ./cx_cookies.txt "https://i.chaoxing.com" -o /dev/null -w "%{http_code}"
```

Treat script `valid: true` as valid. For the legacy curl fallback, treat `200` as likely valid and `302` as expired. Do not assume either state without checking when a cookie file exists.

## Browser Session Versus Script Session

The browser's Chaoxing login state is separate from the local cookie file used by scripts. A manually opened browser tab can redirect to `passport2.chaoxing.com` while `scripts/check_cookie.py` and API-oriented scripts still work with a valid MozillaCookieJar file. When these disagree, report it explicitly and keep using the validated `--cookie-file` path for script operations.

## Login Script

If login is needed:

```bash
python scripts/chaoxing_login_cookie.py --phone "188xxxx1234" --cookie-file ./cx_cookies.txt
```

Omit `--password` when possible so the password is entered without echo. Do not repeat the password in logs or reports.

## Browser Cookie Injection

For browser automation, inject saved cookies through CDP rather than `document.cookie`; `vc3` and `p_auth_token` are httpOnly.

```python
ensure_real_tab()
cdp("Network.enable")
# Load ./cx_cookies.txt with MozillaCookieJar, then call Network.setCookie for each cookie.
cdp("Page.navigate", url="https://i.chaoxing.com")
```

If a browser helper reports `Unknown Target method: activateTarget`, reuse the current real tab and navigate with `Page.navigate`.

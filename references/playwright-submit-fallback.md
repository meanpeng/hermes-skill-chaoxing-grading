# Playwright Submit Fallback

Use this only when the normal browser-harness environment is unavailable and the teacher has explicitly confirmed the exact score list in the current turn.

The safer default is still dry-run:

```bash
python scripts/batch_submit_scores.py --courseid COURSEID --clazzid CLAZZID --work-id WORKID --scores-csv scores.csv
```

## Preconditions

```text
teacher_confirmed_exact_score_list: yes
cookie_file_valid: yes
courseid/clazzid/workId verified: yes
workAnswerId present for every row: yes
manual_review_remaining: 0
```

If any item is not true, do not run a fallback submitter.

## Cookie Injection Pattern

Load MozillaCookieJar cookies and inject them into Playwright context before navigation:

```python
import http.cookiejar

def load_cookies(cookie_file):
    jar = http.cookiejar.MozillaCookieJar(cookie_file)
    jar.load(ignore_discard=True, ignore_expires=True)
    cookies = []
    for cookie in jar:
        cookies.append({
            "name": cookie.name,
            "value": cookie.value,
            "domain": cookie.domain,
            "path": cookie.path or "/",
            "httpOnly": "HttpOnly" in str(cookie._rest),
            "secure": cookie.secure,
        })
    return cookies
```

## Page Write Sequence

For each review URL:

1. Navigate to the `review-work` URL.
2. Verify the page is still logged in and belongs to the expected assignment.
3. Set visible `input.questionScore`.
4. Trigger `input`, `change`, `keyup`, and `blur`.
5. Set hidden `#tmpscore` and `#score`.
6. Call `markAction(1)`.
7. Record the returned page state or status text.

This mirrors `scripts/batch_submit_scores.py`. Setting only the visible input is not enough on many Chaoxing pages.

## Verification

After submission, re-open or re-export the score list and compare:

```text
student_id | expected_score | verified_score | status | match
```

Report mismatches before retrying.

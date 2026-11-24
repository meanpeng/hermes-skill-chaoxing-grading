#!/usr/bin/env python3
"""Pull raw exam mark rows (with markUrl) and every student's server-rendered markpaper page.

Usage (run from the skill directory):
  python3 scripts/exam_markpaper_pull.py --courseid C --clazzid Z --cpi P --relationid R \
      --out-dir ~/c_quiz1_grading [--cookie-file ./cx_cookies.txt] [--include-unsubmitted]

Outputs in --out-dir:
  markrows.json               raw markresult-new rows (submitted, state=1)
  markrows_unsubmitted.json   raw rows with state=0 (未查看/待解答) when --include-unsubmitted
  papers/<sid>_<name>.html    full markpaper HTML per submitted student

Reuses submit_exam_scores.request/mark_result_params so headers/params stay in one place.
`ut` MUST be empty: ut=s returns HTML instead of JSON.
"""
import argparse, json, os, sys, time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chaoxing_discover  # noqa: E402
import submit_exam_scores as S  # noqa: E402


def raw_rows(opener, args, state):
    rows, page, total = [], 1, None
    while True:
        params = S.mark_result_params(args, page)
        params["state"] = state
        body = S.request(opener, S.MARK_RESULT_URL, data=params, method="POST")
        parsed = json.loads(body)
        total = total or int(parsed.get("total") or 0)
        data = parsed.get("data") or []
        rows += data
        if not data or (total and len(rows) >= total):
            break
        page += 1
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cookie-file", default="cx_cookies.txt")
    ap.add_argument("--courseid", required=True)
    ap.add_argument("--clazzid", required=True)
    ap.add_argument("--cpi", required=True)
    ap.add_argument("--relationid", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--include-unsubmitted", action="store_true", help="also fetch state=0 rows (no markpaper)")
    ap.add_argument("--delay", type=float, default=0.6)
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out_dir, "papers"), exist_ok=True)
    opener = chaoxing_discover.make_opener(a.cookie_file)
    referer = ("https://mooc2-ans.chaoxing.com/mooc2-ans/exam/test/marklist?clazzid=%s&courseid=%s&cpi=%s&id=%s"
               % (a.clazzid, a.courseid, a.cpi, a.relationid))

    rows = raw_rows(opener, a, "1")
    json.dump(rows, open(os.path.join(a.out_dir, "markrows.json"), "w"), ensure_ascii=False, indent=1)
    print("submitted rows:", len(rows), "| status:", dict(Counter(r.get("mark") for r in rows)))
    prefixes = Counter(str(r.get("loginName", ""))[:4] for r in rows)
    odd = [(r["loginName"], r["createUserName"]) for r in rows if prefixes[str(r.get("loginName", ""))[:4]] < len(rows) / 2]
    if odd:
        print("NOTE non-roster ID prefixes (retakers/other class?):", odd)

    if a.include_unsubmitted:
        un = raw_rows(opener, a, "0")
        json.dump(un, open(os.path.join(a.out_dir, "markrows_unsubmitted.json"), "w"), ensure_ascii=False, indent=1)
        print("unsubmitted rows:", [(r.get("loginName"), r.get("createUserName"), r.get("mark")) for r in un])

    ok = 0
    for r in rows:
        mu = r.get("markUrl") or ""
        if not mu:
            print("no markUrl:", r.get("createUserName"), r.get("mark"))
            continue
        url = mu if mu.startswith("http") else "https://mooc2-ans.chaoxing.com" + mu
        try:
            html, _ = chaoxing_discover.fetch(opener, url, referer=referer)
        except Exception as exc:  # noqa: BLE001
            print("fail", r.get("createUserName"), exc)
            continue
        if 'class="questionWrap"' not in html:
            print("THIN PAGE (no questionWrap):", r.get("createUserName"), len(html), "chars — check cookie/referer")
        name = str(r.get("createUserName") or "").replace("/", "_")
        open(os.path.join(a.out_dir, "papers", f"{r['loginName']}_{name}.html"), "w").write(html)
        ok += 1
        time.sleep(a.delay)
    print("saved papers:", ok, "->", os.path.join(a.out_dir, "papers"))


if __name__ == "__main__":
    main()

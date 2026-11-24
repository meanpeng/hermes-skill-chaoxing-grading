#!/usr/bin/env python3
"""Parse saved markpaper pages into per-student/per-question data and print the class overview.

Usage: python3 scripts/exam_markpaper_parse.py --dir ~/c_quiz1_grading

Reads  <dir>/papers/<sid>_<name>.html (from exam_markpaper_pull.py)
Writes <dir>/parsed.json          {sid: {name, obj, qs:[{idx,type,qid,full,score,stem,opts,stu,correct,analysis}]}}
       <dir>/subjective_all.txt   every student's subjective answers, for reading/copy checks

Code answers keep their line structure: 简答 bodies are <p>-per-line blocks — join lines with
newline, never collapse whitespace (collapsing glues a C program into one line and breaks gcc).
Objective score = sum of prefilled score inputs on 单选/多选/判断/填空 questions.
"""
import argparse, glob, html as H, json, os, re
from collections import Counter

OBJECTIVE = ("单选题", "多选题", "判断题", "填空题")


def strip(s):
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def lines(block):
    out = []
    for piece in re.split(r"<p>|</p>|<br\s*/?>", block or ""):
        t = strip(piece)
        if t:
            out.append(t)
    return "\n".join(out)


def parse_question(q):
    head = re.match(r'<div class="questionWrap" index="(\d+)" name="([^"]+)"', q)
    ids = re.search(r'<input type="hidden" value="([\d.]+)" id="input(\d+)"', q)
    stem_m = (re.search(r'<h3 class="mark_name".*?<div class="hiddenTitle[^"]*">\s*<p>(.*?)</p>', q, re.S)
              or re.search(r'<h3 class="mark_name">.*?<p>(.*?)</p>', q, re.S))
    if "SubjectStuAnswer" in q:
        stu = lines(re.search(r'<div class="SubjectStuAnswer[^>]*"[^>]*>(.*?)</div>\s*</div>', q, re.S).group(1))
        cm = re.search(r'id="correctanswer_\d+">(.*?)</div>\s*</div>', q, re.S)
        correct = lines(cm.group(1)) if cm else ""
    else:
        sm = re.search(r"学生答案:</i>(.*?)</span>", q, re.S)
        cm = re.search(r"正确答案:</i>(.*?)</span>", q, re.S)
        stu = strip(sm.group(1)) if sm else ""
        correct = strip(cm.group(1)) if cm else ""
    sc = re.search(r'id="score\d+"[^>]*class="inputBranch questionScore"[^>]*value="([\d.]*)"', q)
    ana = re.search(r'objAnswer_analysis[^>]*><p>(.*?)</p>', q, re.S) or re.search(r'AnalysisCon fl"><p>(.*?)</p>', q, re.S)
    opts = [strip(o) for o in re.findall(r'<li class="mark_letter">\s*([A-Z]\.<p>.*?</p>)', q, re.S)]
    return dict(idx=int(head.group(1)), type=head.group(2), qid=ids.group(2), full=float(ids.group(1)),
                score=float(sc.group(1)) if sc and sc.group(1) else None,
                stem=strip(stem_m.group(1)) if stem_m else "", opts=opts, stu=stu, correct=correct,
                analysis=strip(ana.group(1)) if ana else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", required=True)
    a = ap.parse_args()
    students = {}
    for fp in sorted(glob.glob(os.path.join(a.dir, "papers", "*.html"))):
        sid, name = os.path.basename(fp)[:-5].split("_", 1)
        parts = re.split(r'(?=<div class="questionWrap" index="\d+" name=")', open(fp).read())[1:]
        qs = [parse_question(q) for q in parts]
        obj = sum(q["score"] for q in qs if q["type"] in OBJECTIVE and q["score"] is not None)
        students[sid] = dict(name=name, qs=qs, obj=obj)
    json.dump(students, open(os.path.join(a.dir, "parsed.json"), "w"), ensure_ascii=False, indent=1)
    first = next(iter(students.values()))["qs"]
    print("students:", len(students), "| questions:", len(first), "| types:", dict(Counter(q["type"] for q in first)))
    dist = sorted(((s["obj"], s["name"]) for s in students.values()), reverse=True)
    print("objective distribution:", dict(sorted(Counter(o for o, _ in dist).items(), reverse=True)))
    print("objective mean:", round(sum(o for o, _ in dist) / len(dist), 1), "of", sum(q["full"] for q in first if q["type"] in OBJECTIVE))
    print("objective ranking:", " ".join(f"{n}{o:g}" for o, n in dist))
    for q in first:
        if q["type"] in OBJECTIVE:
            wrong = [s["name"] for s in students.values() if next(x for x in s["qs"] if x["qid"] == q["qid"])["score"] == 0]
            if wrong:
                print(f"  Q{q['idx']} {q['type']} key={q['correct']} wrong={len(wrong)}: {' '.join(wrong)}")
    with open(os.path.join(a.dir, "subjective_all.txt"), "w") as f:
        for sid, s in sorted(students.items()):
            f.write(f"\n===== {sid} {s['name']} objective={s['obj']:g} =====\n")
            for q in s["qs"]:
                if q["type"] not in OBJECTIVE:
                    f.write(f"[Q{q['idx']} {q['type']} {q['full']:g}分]\n{s['name']}: {q['stu']}\n--- 参考: {q['correct']}\n--- 要点: {q['analysis']}\n")
    subj = [q for q in first if q["type"] not in OBJECTIVE]
    for q in subj:
        print(f"\nsubjective Q{q['idx']} ({q['full']:g}): {q['stem'][:100]}\n  key: {q['correct'][:120]}\n  rubric: {q['analysis'][:120]}")
    for q in subj:
        blanks = [s["name"] for s in students.values() if not next(x for x in s["qs"] if x["qid"] == q["qid"])["stu"].strip()]
        if blanks:
            print(f"  Q{q['idx']} blank: {' '.join(blanks)}")


if __name__ == "__main__":
    main()

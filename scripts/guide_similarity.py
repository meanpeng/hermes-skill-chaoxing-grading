#!/usr/bin/env python3
"""Guide-copy + template-discounted similarity evidence for Chaoxing report grading.

Run AFTER extract_all.py + parse_docs.py (needs <workdir>/docs/ and manifest.json).
Recipe: references/guide-copy-check.md.

Inputs:
  --workdir  experiment grading dir (contains docs/ and manifest.json)
  --guide    实验指导书 .docx or .txt
Outputs:
  <workdir>/guide_text.txt      normalized guide text
  <workdir>/own_analysis.json   per-student: cls/sid/name/tlen/guide_matched/template_len/
                                net_own/n_img/own_img/shared_img/partners
  <workdir>/net_text_sim.json   pairs above threshold: [net_pct, raw_pct, sid_a, sid_b, net_chars]
Prints top pairs and students with 0 own experiment images.
"""
import argparse
import difflib
import io
import itertools
import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict

NSW = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

# Shared report-template scaffolding (成绩统计表 / covers / headers / checkbox line / prompts).
TPL_PATS = [
    r'实验/实训成绩统计表.{0,40}总成绩教师签名',
    r'实验/实训报告册.{0,200}任课教师：闵鹏',
    r'成都锦城学院实验/实训报告.{0,80}任课教师闵鹏',
    r'任课教师：闵鹏开课时间：202[0-9][^课]{0,14}202[0-9]年9月2[0-9]日',
    r'□演示性实验□验证性实验.{0,40}设计性实训',
    r'（描述完成本次实验的收获或心得体会.{0,60}建议等）',
]


def disable_crc():
    zipfile.ZipExtFile._update_crc = lambda self, nd: (
        setattr(self, '_running_crc', 0), setattr(self, '_expected_crc', 0), nd)[2]


def docx_text(path):
    try:
        with zipfile.ZipFile(path) as z:
            doc = z.read('word/document.xml').decode('utf-8', errors='replace')
    except Exception:
        with zipfile.ZipFile(io.BytesIO(open(path, 'rb').read())) as z:
            doc = z.read('word/document.xml').decode('utf-8', errors='replace')
    if '<w:document' not in doc and '<w:body' not in doc:  # WordML flat XML fallback
        return re.sub(r'\s+', '', ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', doc)))
    root = ET.fromstring(doc)
    return re.sub(r'\s+', '', ''.join(
        ''.join(t.text or '' for t in p.iter(NSW + 't')) for p in root.iter(NSW + 'p')))


def load_guide(path):
    if path.lower().endswith('.docx'):
        return docx_text(path)
    return re.sub(r'\s+', '', open(path, encoding='utf-8').read())


def student_text(workdir, sid):
    cand = sorted(f for f in os.listdir(os.path.join(workdir, 'docs')) if f.startswith(sid + '_'))
    if not cand:
        return ''
    return docx_text(os.path.join(workdir, 'docs', cand[0]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--workdir', required=True)
    ap.add_argument('--guide', required=True, help='指导书 .docx or .txt')
    ap.add_argument('--min-block', type=int, default=50,
                    help='min matching-block chars counted into guide_matched (default 50)')
    ap.add_argument('--common-image-frac', type=float, default=0.5,
                    help='image hash present in >= this fraction of reports counts as crest/template')
    ap.add_argument('--report-threshold', type=float, default=30.0,
                    help='net %% similarity to include a pair in output (default 30)')
    a = ap.parse_args()
    disable_crc()

    guide = load_guide(a.guide)
    with open(os.path.join(a.workdir, 'guide_text.txt'), 'w', encoding='utf-8') as f:
        f.write(guide)
    print('guide chars:', len(guide))

    manifest = json.load(open(os.path.join(a.workdir, 'manifest.json')))

    # --- image sharing: crest/template auto-detected, own vs shared per student ---
    hash_owners = defaultdict(set)
    img_by_sid = defaultdict(list)
    for m in manifest:
        for im in m.get('images', []):
            if im.get('corrupt') or 'hash' not in im:
                continue
            hash_owners[im['hash']].add(m['sid'])
            img_by_sid[m['sid']].append(im['hash'])
    n_with_imgs = sum(1 for s in img_by_sid if img_by_sid[s])
    common = {h for h, owners in hash_owners.items()
              if n_with_imgs and len(owners) >= a.common_image_frac * n_with_imgs}
    print(f'distinct image hashes: {len(hash_owners)} | common/template hashes excluded: {len(common)}')

    # --- per-student guide + template footprint ---
    rows = []
    texts = {}
    for m in manifest:
        sid = m['sid']
        ta = student_text(a.workdir, sid)
        texts[sid] = ta
        sm = difflib.SequenceMatcher(None, ta, guide, autojunk=False) if ta else None
        blocks = [b for b in sm.get_matching_blocks() if b.size >= a.min_block] if sm else []
        guide_matched = sum(b.size for b in blocks)
        tpl = 0
        for pat in TPL_PATS:
            for mt in re.finditer(pat, ta):
                tpl += mt.end() - mt.start()
        own_imgs = shared_imgs = 0
        partners = defaultdict(int)
        for h in img_by_sid.get(sid, []):
            if h in common:
                continue
            others = hash_owners[h] - {sid}
            if others:
                shared_imgs += 1
                for o in others:
                    partners[o] += 1
            else:
                own_imgs += 1
        rows.append({
            'cls': m.get('class', '?'), 'sid': sid, 'name': m.get('name', ''),
            'tlen': len(ta), 'guide_matched': guide_matched,
            'template_len': tpl, 'net_own': max(0, len(ta) - guide_matched - tpl),
            'n_img': len(img_by_sid.get(sid, [])), 'own_img': own_imgs,
            'shared_img': shared_imgs, 'partners': dict(partners),
        })

    json.dump(rows, open(os.path.join(a.workdir, 'own_analysis.json'), 'w'),
              ensure_ascii=False, indent=1)

    # --- net pairwise similarity ---
    R = {r['sid']: r for r in rows}
    pairs = []
    for (a_sid, ta), (b_sid, tb) in itertools.combinations(
            (s for s in texts.items() if s[1]), 2):
        sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
        matched = sum(x.size for x in sm.get_matching_blocks())
        ban = min(R[a_sid]['guide_matched'] + R[a_sid]['template_len'],
                  R[b_sid]['guide_matched'] + R[b_sid]['template_len'])
        net = max(0, matched - ban)
        netr = net / min(len(ta), len(tb)) * 100
        rawr = matched / min(len(ta), len(tb)) * 100
        if netr >= a.report_threshold or (netr >= a.report_threshold / 2 and net >= 600):
            pairs.append([round(netr, 1), round(rawr, 1), a_sid, b_sid, net])
    pairs.sort(reverse=True)
    json.dump(pairs, open(os.path.join(a.workdir, 'net_text_sim.json'), 'w'), ensure_ascii=False)

    print(f'\n=== pairs net>={a.report_threshold}% ({len(pairs)}) ===')
    print(f"{'net':>6}{'raw':>6}  pair  net_chars")
    for netr, rawr, x, y, net in pairs[:25]:
        print(f'{netr:5.1f}%{rawr:5.1f}%  {x[-3:]}{R[x]["name"]:<4} x {y[-3:]}{R[y]["name"]:<4}  {net}')

    print('\n=== students with 0 own experiment images ===')
    for r in sorted(rows, key=lambda x: (x['cls'], x['sid'])):
        if r['own_img'] == 0:
            print(f"{r['cls']} {r['sid']} {r['name']:<5} 自有字{r['net_own']:5} "
                  f"图{r['n_img']} 全共享{r['shared_img']}")


if __name__ == '__main__':
    main()

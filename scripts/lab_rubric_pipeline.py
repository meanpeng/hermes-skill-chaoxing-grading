#!/usr/bin/env python3
"""C语言实验 评分流水线（规则见 references/c-lab-rubric.md）

  packets  --exp exp2 --dir ~/clang_exp2_grading --guide 指导书_实验二.docx --out packets/exp2
            每生导出独有截图(CRC容错) + 全文/自有文本 → packets/<sid>/ + index.json
  score    --exp exp2 --dir ~/clang_exp2_grading --packets packets/exp2 --results results/exp2_*.json --rubric rubric_exp2.json
            汇总子代理判定 → 规则分 + 文本相似/同字节图 → table.csv / report.md

子代理每生输出 schema（judge）:
 {"sid","name","items":[{"key","done":bool,"evidence"}],"own_content":{"level":0|0.5|1|2,"evidence"},
  "fixes":[{"n","how","evidence"}],"questions":[{"n","quality":"full|brief","evidence"}],
  "text":{"ai_traces":bool,"notes"},"plagiarism_notes":"","flags":""}
"""
import argparse, csv, glob, hashlib, json, os, re, sys, zipfile, difflib, collections

def docx_text(p):
    try:
        z = zipfile.ZipFile(p); x = z.read('word/document.xml').decode('utf8', 'ignore')
        paras = re.findall(r'<w:p[ >].*?</w:p>', x, flags=re.S)
        out = []
        for para in paras:
            t = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', para))
            if t.strip(): out.append(t.strip())
        return '\n'.join(out)
    except Exception:
        return ''

def docx_images(p):
    """CRC 容错读取 word/media。返回 [(name, bytes)]"""
    saved = zipfile.ZipExtFile._update_crc
    zipfile.ZipExtFile._update_crc = lambda self, data: None
    try:
        z = zipfile.ZipFile(p); out = []
        for n in z.namelist():
            if n.startswith('word/media/') and not n.endswith('/'):
                try: out.append((n, z.read(n)))
                except Exception: pass
        return out
    except Exception:
        return []
    finally:
        zipfile.ZipExtFile._update_crc = saved

def load_rubric(path):
    return json.load(open(path, encoding='utf-8'))

# ---------------------------------------------------------------- packets
def cmd_packets(a):
    rub = load_rubric(a.rubric)
    corpus = sorted(glob.glob(os.path.join(a.dir, a.corpus_glob)))
    guide_imgs = {hashlib.md5(b).hexdigest() for _, b in docx_images(os.path.join(a.dir, a.guide))} if a.guide else set()
    owners = collections.defaultdict(set); imgs = {}; texts = {}
    for d in corpus:
        sid = os.path.basename(d).split('_')[0]
        for p in glob.glob(d + '/**/*', recursive=True):
            if p.lower().endswith('.docx'):
                texts.setdefault(sid, '')
                texts[sid] += '\n' + docx_text(p)
                for n, b in docx_images(p):
                    h = hashlib.md5(b).hexdigest(); owners[h].add(sid); imgs[h] = b
            elif p.lower().endswith(('.jpg', '.jpeg', '.png')):
                b = open(p, 'rb').read(); h = hashlib.md5(b).hexdigest(); owners[h].add(sid); imgs[h] = b
    os.makedirs(a.out, exist_ok=True)
    index = {'exp': a.exp, 'rubric': rub, 'students': []}
    for d in corpus:
        sid = os.path.basename(d).split('_')[0]
        name = os.path.basename(d).split('_', 1)[-1] if '_' in os.path.basename(d) else sid
        sd = os.path.join(a.out, sid); os.makedirs(sd, exist_ok=True)
        k = 0; shared = 0; guide_hit = 0
        for h, s in owners.items():
            if sid not in s: continue
            if h in guide_imgs: guide_hit += 1; continue
            if len(s) > 1: shared += 1; continue
            k += 1; ext = 'png'
            open(os.path.join(sd, f'{k:02d}.{ext}'), 'wb').write(imgs[h])
        full = texts.get(sid, '')
        own_p = os.path.join(a.dir, 'own_texts', os.path.basename(d) + '.txt')
        own = open(own_p, encoding='utf8', errors='ignore').read() if os.path.exists(own_p) else ''
        open(os.path.join(sd, 'report.txt'), 'w', encoding='utf-8').write(full)
        open(os.path.join(sd, 'own.txt'), 'w', encoding='utf-8').write(own)
        index['students'].append({'sid': sid, 'name': name, 'dir': sd, 'n_img': k, 'n_shared': shared,
                                  'n_guide': guide_hit, 'full_chars': len(full), 'own_chars': len(own), 'text_head': full[:300]})
    # 同字节截图簇（排除指导书图）：>=3 张的簇是互抄实锤信号
    clusters = []
    for h, s in owners.items():
        if len(s) > 1 and h not in guide_imgs:
            clusters.append(sorted(s))
    merged = {}
    for c in clusters:
        merged.setdefault(tuple(c), 0); merged[tuple(c)] += 1
    index['image_clusters'] = [{'owners': list(k), 'n': n} for k, n in sorted(merged.items(), key=lambda kv: -kv[1]) if n >= 2]
    json.dump(index, open(os.path.join(a.out, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"{a.exp}: {len(index['students'])} students, images exported; image clusters:", index['image_clusters'])
    for s in index['students']:
        print(f"  {s['sid']} {s['name']:<6} img={s['n_img']:<3} shared={s['n_shared']:<3} guide={s['n_guide']:<3} full={s['full_chars']:<6} own={s['own_chars']}")

# ---------------------------------------------------------------- score
def norm(t):
    return re.sub(r'\s+', '', t)

def cmd_score(a):
    rub = load_rubric(a.rubric); index = json.load(open(os.path.join(a.packets, 'index.json'), encoding='utf-8'))
    judge = {}
    for f in sorted(glob.glob(a.results)):
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception as e:
            print('bad json', f, e); continue
        for j in (d if isinstance(d, list) else [d]):
            if isinstance(j, dict) and j.get('sid'): judge[str(j['sid'])] = j
    # 可选：文本重判结果覆盖 fixes/questions（图片判定保留 how=terminal 的终端演示项）
    if getattr(a, 'textfix', None):
        import glob as _g
        for f in _g.glob(os.path.join(a.textfix, '*.json')):
            try:
                t = json.load(open(f, encoding='utf-8'))
            except Exception:
                continue
            sid = str(t.get('sid')); j = judge.get(sid)
            if not j: continue
            term = [x for x in j['fixes'] if (x.get('how') or '').lower() == 'terminal']
            text = [x for x in t.get('fixes', []) if (x.get('how') or '').strip()]
            seen = {x['n'] for x in term}
            j['fixes'] = term + [x for x in text if x['n'] not in seen]
            j['questions'] = t.get('questions', [])
            j.setdefault('text', {})['notes'] = (j.get('text', {}).get('notes', '') + ' | ' + t.get('text', {}).get('notes', '')).strip(' |')
            if t.get('text', {}).get('ai_traces'): j['text']['ai_traces'] = True
            if t.get('plagiarism_notes'): j['plagiarism_notes'] = (j.get('plagiarism_notes', '') + ' | ' + t['plagiarism_notes']).strip(' |')
    # 文本相似（自有文本去指导书）
    own = {}
    for s in index['students']:
        p = os.path.join(s['dir'], 'own.txt')   # 自有文本（已扣指导书）；report.txt 含指导书会把步骤原文当成"相同段落"
        if not os.path.exists(p): p = os.path.join(s['dir'], 'report.txt')
        own[s['sid']] = norm(open(p, encoding='utf8', errors='ignore').read())
    sids = [s['sid'] for s in index['students']]
    pairs = []
    for i in range(len(sids)):
        for j in range(i + 1, len(sids)):
            x, y = own[sids[i]], own[sids[j]]
            if min(len(x), len(y)) < 200: continue
            sm = difflib.SequenceMatcher(None, x, y, autojunk=False)
            blocks = [b for b in sm.get_matching_blocks() if b.size >= 150]
            longest = max((b.size for b in blocks), default=0)
            if longest >= 350 or (sm.ratio() >= 0.85 and min(len(x), len(y)) >= 400):
                b0 = next((b for b in blocks if b.size == longest), None)
                pairs.append({'a': sids[i], 'b': sids[j], 'longest_common': longest, 'ratio': round(sm.ratio(), 3),
                              'snippet': (x[b0.a:b0.a + longest][:80] if b0 else '')})
    rows = []
    for s in index['students']:
        j = judge.get(s['sid'])
        if not j:
            rows.append({'sid': s['sid'], 'name': s['name'], 'base': None, 'A': None, 'D': None, 'C': None, 'Q': None, 'T': None,
                         'own_chars': s['own_chars'], 'items_done': [], 'n_fix': None, 'n_q': None, 'own_level': None, 'adjust': None,
                         'score_raw': None, 'score': None, 'plagiarism_notes': '', 'flags': 'no judge result', 'ai_traces': None}); continue
        W = rub['weights']
        done = [it for it in j['items'] if it.get('done')]
        A = sum(W['items'].get(it['key'], 0) for it in done)
        D = W['own_content'][str(j['own_content']['level'])]
        fix_done = [f for f in j['fixes'] if (f.get('how') or '').strip() and (f.get('how') or '').lower() != 'none']
        q_done = [q for q in j['questions'] if (q.get('quality') or '').lower() in ('full', 'brief')]
        C = W['fix_each'] * min(W['fix_max'], len(fix_done))
        Q = sum(W['q_full'] if q.get('quality') == 'full' else W['q_brief'] for q in q_done)
        own_len = s['own_chars']
        T = next(v for lo, v in W['text'] if own_len >= lo)
        base = W['base']
        adj = j.get('adjust', 0)
        total = base + A + D + C + Q + T + adj
        rows.append({'sid': s['sid'], 'name': s['name'], 'base': base, 'A': A, 'D': D, 'C': C, 'Q': Q, 'T': T,
                     'own_chars': own_len, 'items_done': [it['key'] for it in done], 'n_fix': len(fix_done),
                     'n_q': len(q_done), 'own_level': j['own_content']['level'], 'adjust': adj,
                     'score_raw': round(total, 1), 'score': min(rub['cap'], int(total + 0.5)),
                     'plagiarism_notes': j.get('plagiarism_notes', ''), 'flags': j.get('flags', ''),
                     'ai_traces': j.get('text', {}).get('ai_traces', False)})
    out_csv = a.out_csv or os.path.join(a.packets, 'table.csv')
    with open(out_csv, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    json.dump({'pairs': pairs}, open(os.path.join(a.packets, 'pairs.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"{'学号':<10}{'姓名':<6}{'分':>4}{'A':>4}{'D':>3}{'C':>4}{'Q':>4}{'T':>3}{'字':>6}  完成 | 找错/题 | 备注")
    for r in sorted(rows, key=lambda r: -(r.get('score') or 0)):
        if r.get('score') is None: print(r['sid'], r['name'], r.get('flags')); continue
        print(f"{r['sid']:<10}{r['name']:<6}{r['score']:>4}{r['A']:>4}{r['D']:>3}{r['C']:>4.1f}{r['Q']:>4.1f}{r['T']:>3}{r['own_chars']:>6}  {','.join(r['items_done'])} | {r['n_fix']}/{r['n_q']} | {r['flags'][:50]}")
    print("\n文本逐字相同段落 ≥300 字的对:")
    for p in sorted(pairs, key=lambda p: -p['longest_common']): print(" ", p)
    print("\n->", out_csv)

# ---------------------------------------------------------------- tasks (派发上下文)
def build_requirements(rub):
    L = []
    for it in rub['items_desc']:
        L.append(f"- {it['key']}: {it['desc']}")
    L.append('')
    L.append(rub.get('own_content_desc', ''))
    fx = rub.get('fixes_desc') or []
    if fx:
        L.append('找错 %d 项：%s。算做了 = 终端演示了报错/异常输出，或 own.txt 里用自己话写了现象+原因+改正；照抄指导书描述不算。' % (len(fx), '  '.join(f'({i+1}) {d}' for i, d in enumerate(fx))))
    if rub.get('questions'):
        L.append(f"思考题 {rub['questions']} 题：own.txt 里“结果与分析/思考”段 1~{rub['questions']} 编号自己写的答案；一两句极简 = brief。")
    else:
        L.append('无思考题（questions 留空）。')
    return '\n'.join(L)

def cmd_tasks(a):
    rub = load_rubric(a.rubric); index = json.load(open(os.path.join(a.packets, 'index.json'), encoding='utf-8'))
    req = build_requirements(rub); keys = [it['key'] for it in rub['items_desc']]
    res_dir = os.path.abspath(os.path.join(a.results_dir or (a.packets + '/../../results'), a.exp))
    os.makedirs(a.out, exist_ok=True)
    students = [s for s in index['students'] if s['n_img'] > 0 or not a.pass2]
    if a.pass2:
        judge = {}
        for f in glob.glob(os.path.join(a.results, '*.json')):
            try:
                d = json.load(open(f, encoding='utf-8'))
                for j in (d if isinstance(d, list) else [d]): judge[str(j['sid'])] = j
            except Exception: pass
        students = [s for s in students if s['sid'] in judge and len([i for i in judge[s['sid']]['items'] if i.get('done')]) < len(keys) and s['n_img'] > 0]
    bins = []
    for s in sorted(students, key=lambda s: -s['n_img']):
        for b in bins:
            if len(b) < a.max_students and sum(x['n_img'] for x in b) + s['n_img'] <= a.max_images: b.append(s); break
        else: bins.append([s])
    head1 = (f"你是 C语言「{rub['exp']}」报告评分助手，逐生判定后写 JSON。只做识图+读文本，不参考任何已有分数。识图用 vision_analyze（一图一调，每轮 3-4 张并行）；报错(如 429)就等 20s 重试一次。\n"
             f"【实验要求】\n{req}\n"
             "【判定标准】items.done=true 仅当截图里有该项对应的 gcc 运行输出/证据（只贴代码无输出不算；找错演示的错误输出不算程序跑通）。\n"
             "**合并程序规则：一张截图里一个程序跑出的输出如果同时覆盖多个任务（如 main.c 先输出 hello 再输出名片；变量程序里又算了平均分；gcc -v 和 settings.json 同屏），那几个任务都算 done=true。**\n"
             "**目录/文件名不是指导书要求的不扣分，只要程序功能和运行输出对得上就算 done。**\n"
             f"【每个学生目录】{os.path.abspath(a.packets)}/<sid>/ ：report.txt = 报告全文（含指导书步骤）；own.txt = 扣掉指导书原文后的学生自有文字；NN.png = 该生独有截图。\n"
             "**找错/思考题只看 own.txt 和截图**——report.txt 里的找错题目/思考题原文是指导书内容，不算学生做的。\n"
             "【步骤】每生：read own.txt（必要时看 report.txt 了解结构）→ 每张图 vision_analyze（问：软件界面、.c 文件名、终端路径、代码要点、运行输出逐行；有没有合并程序）→ 判定。无独有截图的学生只按文本判（items 全 false）。\n"
             f"【输出】每人一个 JSON 写到 {res_dir}/<sid>.json：\n"
             '{"sid","name","items":[{"key":"' + keys[0] + '","done":true,"evidence":"img03: <输出行>"}, ...共 ' + str(len(keys)) + ' keys: ' + ','.join(keys) + '],\n'
             ' "own_content":{"level":2,"evidence":""},"fixes":[{"n":1,"how":"terminal|text","evidence":""}],\n'
             ' "questions":[{"n":1,"quality":"full|brief","evidence":""}],"text":{"ai_traces":false,"notes":""},"plagiarism_notes":"","flags":""}\n'
             '**未做的找错/思考题不要列进 fixes/questions。** 最终回复只回 {"written":["sid",...]}。\n'
             "【学生】")
    head2 = (f"你是 C语言「{rub['exp']}」报告复核助手（第二遍：合并程序复核）。第一遍按“一张截图=一个程序”判，可能漏算了一个程序同时做多个任务、或多个任务同屏的情况。只看图，不参考分数。识图用 vision_analyze（一图一调，每轮 3-4 张并行）；429 就等 20s 重试。\n"
             f"【任务判定标准（程序功能和输出对得上就算，目录/文件名不重要）】\n{req}\n"
             "**合并程序规则：一张截图里一个程序跑出的输出如果同时包含多个任务的输出，那几个任务都算 done=true。已判 done 的不用重判。**\n"
             f"【每个学生】目录 {os.path.abspath(a.packets)}/<sid>/ 下 NN.png 为该生截图。\n"
             f"【输出】每人一个 JSON 写到 {res_dir.replace('/' + a.exp, '/' + a.exp + '_pass2')}/<sid>.json：\n"
             '{"sid","name","items":[{"key":"' + keys[0] + '","done":true,"evidence":""}, ...共 ' + str(len(keys)) + ' keys，包含第一遍已 done 的（照抄）和本轮新判的],"own_content":{"level":2,"evidence":""},"changed":"本轮新增了哪些 key，没有就写 none"}\n'
             '最终回复只回 {"written":["sid",...]}。\n【学生】')
    judge = {}
    if a.pass2:
        for f in glob.glob(os.path.join(a.results, '*.json')):
            try:
                d = json.load(open(f, encoding='utf-8'))
                for j in (d if isinstance(d, list) else [d]): judge[str(j['sid'])] = j
            except Exception: pass
    for i, b in enumerate(bins):
        lines = []
        for s in b:
            if a.pass2:
                done = [x['key'] for x in judge[s['sid']]['items'] if x.get('done')]
                todo = [k for k in keys if k not in done]
                lines.append(f"{s['sid']} {s['name']} 已done={','.join(done) or '无'}；待查={','.join(todo)} ({s['n_img']}图)")
            else:
                lines.append(f"{s['sid']} {s['name']} {os.path.abspath(a.packets)}/{s['sid']} ({s['n_img']}图)" if s['n_img'] else f"{s['sid']} {s['name']} {os.path.abspath(a.packets)}/{s['sid']} (无独有截图，只按文本判)")
        ctx = (head2 if a.pass2 else head1) + '；'.join(lines)
        open(os.path.join(a.out, f"{a.exp}{'_pass2' if a.pass2 else ''}_T{i+1}.txt"), 'w', encoding='utf-8').write(ctx)
        print(f"T{i+1}: " + ' | '.join(f"{s['name']}({s['n_img']})" for s in b))
    print(f"-> {a.out}")

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('packets'); p.add_argument('--exp', required=True); p.add_argument('--dir', required=True)
    p.add_argument('--guide', required=True); p.add_argument('--rubric', required=True); p.add_argument('--out', required=True)
    p.add_argument('--corpus-glob', default='corpus/*/*'); p.set_defaults(fn=cmd_packets)
    s = sp.add_parser('score'); s.add_argument('--exp', required=True); s.add_argument('--dir', required=True)
    s.add_argument('--packets', required=True); s.add_argument('--results', required=True, help='glob of judge json files')
    s.add_argument('--rubric', required=True); s.add_argument('--out-csv'); s.add_argument('--textfix', help='dir of text-only re-judge json'); s.set_defaults(fn=cmd_score)
    t = sp.add_parser('tasks'); t.add_argument('--exp', required=True); t.add_argument('--rubric', required=True); t.add_argument('--packets', required=True)
    t.add_argument('--out', required=True); t.add_argument('--pass2', action='store_true'); t.add_argument('--results', help='pass2: dir of pass1 json')
    t.add_argument('--results-dir', help='where children write results (default <packets>/../../results/<exp>)')
    t.add_argument('--max-students', type=int, default=3); t.add_argument('--max-images', type=int, default=22); t.set_defaults(fn=cmd_tasks)
    a = ap.parse_args(); a.fn(a)

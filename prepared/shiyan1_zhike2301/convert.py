#!/usr/bin/env python3
"""将每个学生的实验报告(.docx优先)转成 PDF,再转成 PNG 图片。"""
import os, subprocess, glob, sys

BASE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else '/home/ubuntu/.hermes/skills/productivity/chaoxing-assignment-grading/prepared/shiyan1_zhike2301'
BASE = '/home/ubuntu/.hermes/skills/productivity/chaoxing-assignment-grading/prepared/shiyan1_zhike2301'
IMG_ROOT = os.path.join(BASE, '_images')
os.makedirs(IMG_ROOT, exist_ok=True)

results = []
for d in sorted(os.listdir(BASE)):
    if d.startswith('_'):
        continue
    stu_dir = os.path.join(BASE, d)
    if not os.path.isdir(stu_dir):
        continue
    # 找 docx (优先) 或 doc
    files = [f for f in os.listdir(stu_dir) if f.lower().endswith('.docx')]
    chosen = None
    if files:
        chosen = sorted(files)[0]
    else:
        docs = [f for f in os.listdir(stu_dir) if f.lower().endswith('.doc')]
        chosen = sorted(docs)[0] if docs else None
    if not chosen:
        results.append((d, 'NO_FILE', 0))
        continue
    src = os.path.join(stu_dir, chosen)
    out_pdf_dir = os.path.join(stu_dir, '_pdf')
    os.makedirs(out_pdf_dir, exist_ok=True)
    # soffice 转 pdf
    r = subprocess.run(
        ['soffice', '--headless', '--convert-to', 'pdf', '--outdir', out_pdf_dir, src],
        capture_output=True, text=True, timeout=120)
    pdf = glob.glob(os.path.join(out_pdf_dir, '*.pdf'))
    if not pdf:
        results.append((d, 'PDF_FAIL: ' + (r.stderr or '')[-100:], 0))
        continue
    pdf = pdf[0]
    img_dir = os.path.join(IMG_ROOT, d)
    os.makedirs(img_dir, exist_ok=True)
    # pdftoppm 转 png
    r2 = subprocess.run(
        ['pdftoppm', '-png', '-r', '110', pdf, os.path.join(img_dir, 'page')],
        capture_output=True, text=True, timeout=120)
    pngs = sorted(glob.glob(os.path.join(img_dir, '*.png')))
    results.append((d, 'OK', len(pngs)))

for name, status, npages in results:
    print(f'{name} | {status} | pages={npages}')
print('TOTAL_STUDENTS', len(results))

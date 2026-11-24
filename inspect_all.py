#!/usr/bin/env python3
"""Inspect all student submissions for detailed grading."""
import csv, os, re, zipfile, json
from xml.etree import ElementTree as ET

def read_docx_text(path):
    try:
        from docx import Document
        doc = Document(path)
        text = '\n'.join([p.text for p in doc.paragraphs if p.text.strip()])
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        text += '\n' + cell.text.strip()
        return text
    except Exception as e:
        try:
            with zipfile.ZipFile(path) as z:
                with z.open('word/document.xml') as f:
                    content = f.read().decode('utf-8', errors='replace')
                    texts = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', content)
                    return ''.join(texts)
        except:
            return f'ERROR: {e}'

def read_doc_text(path):
    with open(path, 'rb') as f:
        header = f.read(200)
    if b'<?xml' in header or b'w:wordDocument' in header:
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            texts = []
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag == 't' and elem.text:
                    texts.append(elem.text)
                elif tag == 'p':
                    texts.append('\n')
            return ''.join(texts)
        except:
            pass
    return read_docx_text(path)

csv_path = 'prepared/yikewen-wulianwang/物联网2303-闵-一课一文(word)-54303389/grading_metrics.csv'
students = []
with open(csv_path, encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rp = row['report_path']
        if not os.path.exists(rp):
            students.append({**row, 'full_text': 'FILE_NOT_FOUND', 'full_len': 0})
            continue
        if rp.endswith('.docx'):
            text = read_docx_text(rp)
        else:
            text = read_doc_text(rp)
        students.append({**row, 'full_text': text, 'full_len': len(text)})

results = []
for s in students:
    text = s['full_text']
    full_len = len(text)
    char_count = int(s.get('char_count', 0))

    # Check for personal understanding/critical thinking section
    personal_keywords = ['批判', '个人理解', '个人思考', '个人见解', '个人体验',
                         '使用体验', '我的理解', '我的思考', '我认为', '个人观点',
                         '独立见解', '反思', '我的看法', '我的感受', '体会']
    has_personal = any(kw in text for kw in personal_keywords)

    # Check four dimensions
    dim_keywords = ['技术背景', '发展现状', '前沿成果', '未来方向',
                    '发展趋势', '起源', '核心原理', '发展脉络']
    dim_count = sum(1 for kw in dim_keywords if kw in text)

    # Estimate personal section length
    personal_start = -1
    for kw in ['批判性思考', '个人理解', '个人思考', '个人见解', '使用体验',
               '我的思考', '我的理解', '我认为', '个人观点', '反思与',
               '思考与', '批判', '我的看法', '我的感受', '体会']:
        idx = text.find(kw)
        if idx >= 0 and (personal_start < 0 or idx < personal_start):
            personal_start = idx
    personal_chars = full_len - personal_start if personal_start >= 0 else 0

    # Check if meets 1500 char requirement (Chinese chars)
    meets_length = full_len >= 1500
    meets_personal_length = personal_chars >= 500

    # Quality indicators
    has_structure = any(kw in text for kw in ['一、', '二、', '三、', '四、', '1.', '2.', '3.', '4.'])
    has_references = any(kw in text for kw in ['参考', '引用', '文献', '来源', 'Reference'])
    has_specific_tech = any(kw in text for kw in ['Transformer', 'CNN', 'RNN', 'LSTM', 'BERT',
                                                     'GPT', '神经网络', '深度学习', '机器学习',
                                                     '自然语言处理', 'NLP', 'ASR', 'TTS',
                                                     '卷积', '推荐算法', '协同过滤'])

    results.append({
        'student_id': s['student_id'],
        'student_name': s['student_name'],
        'char_count': char_count,
        'full_len': full_len,
        'has_personal': has_personal,
        'personal_chars': personal_chars,
        'dim_count': dim_count,
        'meets_length': meets_length,
        'meets_personal_length': meets_personal_length,
        'has_structure': has_structure,
        'has_references': has_references,
        'has_specific_tech': has_specific_tech,
        'preview': s.get('preview', '')[:150],
        'status': s.get('status', ''),
        'format': s.get('format', ''),
        'report_path': s.get('report_path', ''),
    })

# Print summary
for r in results:
    print(f"=== {r['student_id']} {r['student_name']} ===")
    print(f"  chars={r['char_count']} full_len={r['full_len']} format={r['format']}")
    print(f"  has_personal={r['has_personal']} personal_chars={r['personal_chars']}")
    print(f"  dim_count={r['dim_count']} meets_length={r['meets_length']} meets_personal={r['meets_personal_length']}")
    print(f"  structure={r['has_structure']} refs={r['has_references']} specific_tech={r['has_specific_tech']}")
    print(f"  preview: {r['preview'][:120]}")
    print()

# Also check: how many students in zip vs expected
print(f"\nTotal students in zip: {len(results)}")
print(f"Expected submitted: 44")

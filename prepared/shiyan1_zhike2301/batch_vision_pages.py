#!/usr/bin/env python3
"""逐页用 glm-4v-flash 分析实验报告,结果存 JSON。"""
import os, base64, json, urllib.request, time

BASE = '/home/ubuntu/.hermes/skills/productivity/chaoxing-assignment-grading/prepared/shiyan1_zhike2301'
IMG_ROOT = os.path.join(BASE, '_images')
OUT = os.path.join(BASE, 'vision_results.json')

def load_env():
    env = {}
    with open('/home/ubuntu/.hermes/.env') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k] = v
    return env

ENV = load_env()
API_KEY = ENV.get('GLM_API_KEY', '')
BASE_URL = ENV.get('GLM_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4').rstrip('/')
MODEL = 'glm-4v-flash'

PROMPT = """这是学生实验报告《实验一:实时摄像头数据采集》的一页。请如实描述这一页的内容,重点回答:
1. 这一页是什么部分(封面/实验目的/原理/步骤/代码/结果截图/结果分析/总结)?
2. 如果页面上有截图或图片,描述图片内容(是不是摄像头采集的画面?显示的是人脸、场景、还是监视界面?)
3. 如果有代码,简单说明是什么代码。

用中文简洁回答,3-5句话即可,不要用JSON格式。"""

def glm_vision(img_path, prompt=PROMPT):
    b64 = base64.b64encode(open(img_path, 'rb').read()).decode()
    url = BASE_URL + '/chat/completions'
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": prompt}
        ]}],
        "max_tokens": 400,
        "temperature": 0.2
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=120)
    d = json.loads(r.read().decode())
    return d['choices'][0]['message']['content']

def main():
    results = {}
    if os.path.exists(OUT):
        results = json.load(open(OUT))
    students = sorted([d for d in os.listdir(IMG_ROOT) if os.path.isdir(os.path.join(IMG_ROOT, d))])
    for s in students:
        if s in results:
            continue
        sdir = os.path.join(IMG_ROOT, s)
        pngs = sorted([f for f in os.listdir(sdir) if f.endswith('.png')])
        pages = {}
        for p in pngs:
            key = p.replace('.png', '')
            if key in results.get(s, {}):
                pages[key] = results[s][key]
                continue
            try:
                txt = glm_vision(os.path.join(sdir, p))
                pages[p.replace('.png', '')] = txt
                print(f'{s} / {p}: {txt[:80]}', flush=True)
            except Exception as e:
                pages[p.replace('.png', '')] = f'ERROR: {e}'
                print(f'{s} / {p}: ERROR {e}', flush=True)
            time.sleep(0.3)
        results[s] = pages
        json.dump(results, open(OUT, 'w'), ensure_ascii=False, indent=1)
    print('DONE', len(results))

if __name__ == '__main__':
    main()

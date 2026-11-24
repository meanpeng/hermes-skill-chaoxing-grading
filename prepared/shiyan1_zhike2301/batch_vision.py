#!/usr/bin/env python3
"""批量：每份实验报告拼成长图，用 glm-4v-flash 视觉评估。"""
import os, base64, json, urllib.request
from PIL import Image

BASE = '/home/ubuntu/.hermes/skills/productivity/chaoxing-assignment-grading/prepared/shiyan1_zhike2301'
IMG_ROOT = os.path.join(BASE, '_images')

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

PROMPT = """你是一名大学《人工智能与深度学习》课程助教,正在批改学生实验报告《实验一:实时摄像头数据采集》。

请仔细看这份实验报告(一张长图,从上到下是报告的各个页面),从以下维度评估并输出 JSON:

1. 基本信息是否完整(姓名/学号/班级/课程名)
2. 实验目的与原理是否阐述清楚
3. 实验步骤/流程是否完整
4. 是否贴了代码(代码是否完整、是否关键部分)
5. 摄像头采集结果截图:有没有真实截图?几张?截图里是否能看到摄像头成功采集到的画面(比如人脸、场景、监视画面)?
6. 结果分析、实验总结/心得是否写了

最后给出:总体完成质量评价(一两句话),以及你觉得明显的扣分点或亮点。

只输出 JSON,格式如下(不要输出其他文字):
{"基本信息完整": true/false, "实验目的原理": "简述", "步骤完整": "简述", "有无代码": true/false, "代码质量": "简述", "截图数量": 数字, "截图是否真实采集画面": "是/否/部分", "结果分析总结": "简述", "总体评价": "一句话", "扣分点或亮点": "简述"}"""

def glm_vision(b64, prompt=PROMPT):
    url = BASE_URL + '/chat/completions'
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": prompt}
        ]}],
        "max_tokens": 600,
        "temperature": 0.1
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=180)
    d = json.loads(r.read().decode())
    return d['choices'][0]['message']['content']

def build_long_image(student_dir, max_width=900):
    pngs = sorted([f for f in os.listdir(student_dir) if f.endswith('.png')])
    imgs = []
    for p in pngs:
        im = Image.open(os.path.join(student_dir, p)).convert('RGB')
        if im.width > max_width:
            h = int(im.height * max_width / im.width)
            im = im.resize((max_width, h))
        imgs.append(im)
    total_h = sum(i.height for i in imgs)
    w = max(i.width for i in imgs)
    canvas = Image.new('RGB', (w, total_h), 'white')
    y = 0
    for im in imgs:
        canvas.paste(im, (0, y))
        y += im.height
    return canvas

if __name__ == '__main__':
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else None
    students = sorted([d for d in os.listdir(IMG_ROOT) if os.path.isdir(os.path.join(IMG_ROOT, d))])
    if target:
        students = [s for s in students if target in s]
    for s in students:
        print(f'=== {s} ===', flush=True)
        canvas = build_long_image(os.path.join(IMG_ROOT, s))
        # 压缩成 jpeg 存临时文件，控制 base64 大小
        tmp = '/tmp/long_' + s.replace('/', '_') + '.jpg'
        canvas.save(tmp, 'JPEG', quality=80)
        sz = os.path.getsize(tmp)
        print(f'  长图 {canvas.width}x{canvas.height}, {sz/1024:.0f}KB', flush=True)
        if canvas.height > 9000:
            print('  [超高,可能超限,需分段]', flush=True)
            # 分段:每段最多约 9000px 高
            y = 0
            seg = 0
            while y < canvas.height:
                seg += 1
                box = canvas.crop((0, y, canvas.width, min(y+9000, canvas.height)))
                stmp = f'/tmp/seg_{s.replace("/","_")}_{seg}.jpg'
                box.save(stmp, 'JPEG', quality=80)
                b64 = base64.b64encode(open(stmp, 'rb').read()).decode()
                print(f'    seg{seg} {len(b64)/1024:.0f}KB base64', flush=True)
                try:
                    r = glm_vision(b64)
                    print('    ->', r[:400], flush=True)
                except Exception as e:
                    print('    ERROR', e, flush=True)
                y += 9000
        else:
            b64 = base64.b64encode(open(tmp, 'rb').read()).decode()
            print(f'  base64 {len(b64)/1024:.0f}KB', flush=True)
            try:
                r = glm_vision(b64)
                print('  ->', r, flush=True)
            except Exception as e:
                print('  ERROR', e, flush=True)

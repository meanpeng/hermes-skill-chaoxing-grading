#!/usr/bin/env python3
import json, base64, urllib.request

env = {}
with open('/home/ubuntu/.hermes/.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k] = v
API_KEY = env.get('GLM_API_KEY', '')
BASE_URL = env.get('GLM_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4').rstrip('/')

img = '/home/ubuntu/.hermes/skills/productivity/chaoxing-assignment-grading/prepared/shiyan1_zhike2301/_images/233080499-黄娅婷/page-1.png'
b64 = base64.b64encode(open(img, 'rb').read()).decode()

for model in ['glm-5.3-flash', 'glm-4.5v']:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": "这是实验报告封面,简要说说写了什么"}
        ]}],
        "max_tokens": 300,
        "temperature": 0.2
    }
    req = urllib.request.Request(BASE_URL + '/chat/completions', data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=120)
        d = json.loads(r.read().decode())
        print(f'--- {model} ---')
        print(d['choices'][0]['message']['content'][:400])
    except Exception as e:
        print(f'--- {model} ---')
        print('ERROR:', e)

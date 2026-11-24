#!/usr/bin/env python3
"""用 GLM 视觉 API 测试看图能力。"""
import json, base64, urllib.request, os

env = {}
with open('/home/ubuntu/.hermes/.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k] = v

api_key = env.get('GLM_API_KEY', '')
base_url = env.get('GLM_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4').rstrip('/')

img = '/home/ubuntu/.hermes/skills/productivity/chaoxing-assignment-grading/prepared/shiyan1_zhike2301/_images/233080499-黄娅婷/page-1.png'
b64 = base64.b64encode(open(img, 'rb').read()).decode()

def test(model):
    url = base_url + '/chat/completions'
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                {"type": "text", "text": "这是实验报告第一页,简要说说这一页写了什么"}
            ]}
        ],
        "max_tokens": 200
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=90)
        d = json.loads(r.read().decode())
        return d['choices'][0]['message']['content']
    except Exception as e:
        return f"ERROR: {e}"

for m in ['glm-4v-flash', 'glm-4.5v', 'glm-4v-plus']:
    print(f'--- {m} ---')
    print(test(m)[:300])

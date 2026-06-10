#!/usr/bin/env python3
"""ETH EMA 预警推送测试 - 支持多种报警类型 + 飞书 Webhook"""
from flask import Flask, request, redirect, url_for
import os, time, socket, random

try:
    import requests
    HAS_REQUESTS = True
except:
    HAS_REQUESTS = False

app = Flask(__name__)


# ========== 报警类型定义（你可以随便加）==========
ALERT_TYPES = [
    ('golden_cross',      '📈 金叉信号 · 开多',   '【ETH EMA 预警】EMA180 向上穿越 EMA250 → 金叉信号，建议开多'),
    ('dead_cross',        '📉 死叉信号 · 开空',   '【ETH EMA 预警】EMA180 向下穿越 EMA250 → 死叉信号，建议开空'),
    ('price_high',        '⚠️ 价格突破上限',      '【ETH 价格预警】ETH 价格突破 $4,000 上限，当前价格 $4,021.50，注意止盈'),
    ('price_low',         '⚠️ 价格跌破下限',      '【ETH 价格预警】ETH 价格跌破 $3,000 下限，当前价格 $2,985.20，注意止损'),
    ('volatility',        '🌪️ 异常波动',         '【ETH 波动预警】5 分钟内波动超过 3%，当前价格 $3,512.80，注意风险'),
    ('volume_spike',      '📊 成交量异常',        '【ETH 成交量预警】近 1 小时成交量放大 5 倍，可能有大资金入场/出场'),
    ('test_message',      '🧪 测试消息',          '【ETH 测试】这是一条测试消息 %s。如果你看到它，说明 Webhook 配置成功！' % time.strftime('%H:%M:%S')),
]


def _row(label, value, ok=None):
    icon = '✅' if ok is True else ('❌' if ok is False else '·')
    return '<div class="row"><span class="k">%s</span><span class="icon">%s</span><span class="v">%s</span></div>' % (label, icon, str(value).replace('<', '&lt;'))


def _push_feishu(webhook, title, content, timeout=15):
    """飞书机器人推送"""
    if not HAS_REQUESTS:
        raise Exception('requests 库未安装，检查 requirements.txt')
    # 飞书消息格式：{"msg_type": "text", "content": {"text": "..."}}
    text = '%s\n\n%s' % (title, content)
    data = {'msg_type': 'text', 'content': {'text': text}}
    try:
        r = requests.post(webhook, json=data, timeout=timeout)
    except requests.exceptions.ConnectionError as e:
        raise Exception('连接失败: Render 服务器无法访问飞书 API（可能被墙）。错误: %s' % str(e)[:150])
    except socket.timeout:
        raise Exception('连接超时: Render 服务器连不上飞书 API（15 秒无响应）')
    except Exception as e:
        raise Exception('请求异常: %s' % str(e)[:150])

    try:
        j = r.json()
    except:
        raise Exception('飞书返回非 JSON: HTTP %d, Body: %s' % (r.status_code, r.text[:200]))

    # 飞书返回: {"code":0,"msg":"success"} 或 {"code":非0, "msg":"错误"}
    code = j.get('code', j.get('StatusCode', 0))
    if code != 0:
        raise Exception('飞书返回错误 code=%d: %s' % (code, str(j)[:200]))
    return '飞书机器人 (HTTP %d)' % r.status_code


@app.route('/')
def index():
    feishu = os.environ.get('FEISHU_WEBHOOK', '').strip()

    rows = _row('飞书 Webhook', feishu[:50] + '...' if len(feishu) > 50 else feishu if feishu else '(未设置)', bool(feishu))
    rows += _row('Render 环境', '正在运行 · %s' % time.strftime('%Y-%m-%d %H:%M:%S'), True)

    # 生成报警按钮 HTML
    buttons = ''
    for key, title, content in ALERT_TYPES:
        buttons += '<a href="/send?t=%s" class="btn">%s</a>' % (key, title)

    html = '''<!DOCTYPE html><html><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>ETH 预警推送测试</title>
    <style>
      body{font-family:-apple-system,sans-serif;max-width:720px;margin:20px auto;padding:20px;background:#1e1b4b;color:#fff;line-height:1.7}
      h1{margin-bottom:8px}
      h2{margin:22px 0 14px;font-size:17px;color:#a5b4fc}
      .card{background:rgba(255,255,255,0.06);border-radius:14px;padding:18px 20px;margin-bottom:18px;border:1px solid rgba(255,255,255,0.1)}
      .btn{display:inline-block;background:#6366f1;color:#fff;text-decoration:none;padding:12px 20px;border-radius:10px;font-size:14px;font-weight:600;margin:6px;transition:all .2s}
      .btn:hover{background:#818cf8;transform:translateY(-1px)}
      .row{padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:14px;display:flex;align-items:center;flex-wrap:wrap}
      .k{color:#94a3b8;width:180px;flex-shrink:0}
      .icon{width:30px;text-align:center}
      .v{word-break:break-all;flex:1;color:#e2e8f0;font-size:12px}
      .small{font-size:13px;color:#94a3b8;margin-top:8px;line-height:1.8}
      .ok{background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);padding:20px;border-radius:14px;margin-bottom:20px;color:#34d399}
      .fail{background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);padding:20px;border-radius:14px;margin-bottom:20px;color:#f87171}
      code{background:rgba(0,0,0,0.35);padding:3px 8px;border-radius:4px;font-size:12px}
      pre{background:rgba(0,0,0,0.4);padding:14px;border-radius:8px;font-size:12px;white-space:pre-wrap;word-break:break-all;margin-top:10px;color:#cbd5e1}
      .alert-preview{background:rgba(0,0,0,0.3);padding:14px;border-radius:10px;font-size:13px;margin:8px 0;color:#cbd5e1}
    </style></head><body>

    <h1>📧 ETH EMA 预警推送测试</h1>
    <p style="color:#94a3b8;font-size:14px;margin-bottom:20px">飞书 Webhook 推送测试 · 当前时间 %s</p>

    <div class="card"><h2>① 环境变量检查</h2>%s
    <p class="small">在 Render → Environment 设置 <code>FEISHU_WEBHOOK</code> = 你的飞书机器人 Webhook URL</p></div>

    <div class="card"><h2>② 模拟 ETH 报警（点按钮发送）</h2>
    <div style="text-align:center">%s</div>
    <p class="small">点任意按钮 → 云端会调用飞书 Webhook → 飞书群收到消息</p></div>

    <div class="card"><h2>③ 飞书机器人配置说明</h2>
    <p class="small"><b>飞书机器人设置：</b>群设置 → 群机器人 → 添加机器人 → 自定义机器人<br>
    <b>安全设置：</b>如果选了「自定义关键词」，消息中必须包含该关键词才能发送。<br>
    例如你加了关键词「ETH」，当前消息标题包含「ETH EMA 预警」，就可以发送。<br>
    <b>也可以选「加签」（sign）</b>：需要在 URL 或请求体中加签 — 这个功能复杂，建议先用关键词模式测试。</p></div>

    </body></html>
    ''' % (time.strftime('%Y-%m-%d %H:%M:%S'), rows, buttons)
    return html, 200


@app.route('/send')
def send():
    """按 t 参数选择报警类型发送"""
    feishu = os.environ.get('FEISHU_WEBHOOK', '').strip()
    t = request.args.get('t', 'test_message')

    head = '''<!DOCTYPE html><html><head><meta charset="utf-8"><title>发送结果</title>
    <meta name="viewport" content="width=device-width,initial-scale=1"><style>
      body{font-family:-apple-system,sans-serif;max-width:640px;margin:20px auto;padding:20px;background:#1e1b4b;color:#fff;line-height:1.7}
      .ok{background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);padding:20px;border-radius:14px;margin-bottom:20px;color:#34d399}
      .fail{background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);padding:20px;border-radius:14px;margin-bottom:20px;color:#f87171}
      h1{margin-bottom:8px}p{margin:8px 0}.small{font-size:13px;color:#94a3b8}
      code{background:rgba(0,0,0,0.35);padding:2px 6px;border-radius:4px;font-size:12px}
      pre{background:rgba(0,0,0,0.4);padding:14px;border-radius:8px;font-size:12px;white-space:pre-wrap;word-break:break-all;margin-top:10px;color:#cbd5e1}
      a{display:inline-block;background:#6366f1;color:#fff;text-decoration:none;padding:12px 22px;border-radius:10px;font-size:14px;font-weight:600;margin-top:16px;margin-right:10px}
    </style></head><body>'''

    if not feishu:
        return head + '<div class="fail"><h1>❌ 未设置 FEISHU_WEBHOOK</h1><p>去 Render → Environment，加变量 <code>FEISHU_WEBHOOK</code> = 你的飞书 Webhook URL</p><a href="/">返回</a></div></body></html>'

    # 找对应报警
    alert_map = {k: (title, content) for k, title, content in ALERT_TYPES}
    if t not in alert_map:
        t = 'test_message'
    title, content = alert_map[t]

    # 发飞书
    try:
        result = _push_feishu(feishu, title, content)
        return head + '''<div class="ok"><h1>✅ 推送成功！</h1>
        <p>方式：<b>%s</b></p>
        <p>标题：<b>%s</b></p>
        <div class="small">内容：<br><pre>%s</pre></div>
        <p class="small">📱 快去飞书群看有没有收到消息！</p>
        <a href="/">返回首页</a>
        </div></body></html>''' % (result, title, content)
    except Exception as e:
        return head + '''<div class="fail"><h1>❌ 推送失败</h1>
        <p>错误信息：</p>
        <pre>%s</pre>
        <p class="small"><b>常见原因：</b></p>
        <p class="small">1. <b>飞书 API 在 Render 连不上</b>（最常见）→ Render 服务器在国外，飞书 API 可能被墙/超时。试试在本地电脑直接跑 Python 发送测试确认 Webhook 是否有效。</p>
        <p class="small">2. <b>关键词校验失败</b> → 如果机器人设置了自定义关键词，确保消息内容包含该关键词。</p>
        <p class="small">3. <b>Webhook URL 错误</b> → 检查 URL 是否完整正确。</p>
        <p class="small"><b>本地测试命令（在你电脑上跑）：</b></p>
        <pre>python -c "
import requests
r = requests.post('%s', json={'msg_type':'text','content':{'text':'本地测试消息'}})
print('HTTP Status:', r.status_code)
print('Response:', r.text)
"</pre>
        <a href="/">返回首页</a>
        </div></body></html>
        ''' % (str(e), feishu)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print('推送测试启动: http://localhost:%d' % port)
    app.run(host='0.0.0.0', port=port, debug=False)

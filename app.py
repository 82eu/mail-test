#!/usr/bin/env python3
"""极简邮件测试工具 - 部署到 Render 一键测试 Gmail"""
from flask import Flask, request, jsonify
import os, smtplib, ssl, time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)


# 强制所有异常都返回 JSON（不再返回 HTML 500 页面）
@app.errorhandler(Exception)
def _err(e):
    import traceback
    tb = traceback.format_exc()
    return '{"success":false,"error":"'+str(e).replace('"','\"').replace('\n',' ')+'","detail":"'+tb[-500:].replace('"','\"').replace('\n','\\n').replace('\r','')+'"}', 500, {'Content-Type': 'application/json; charset=utf-8'}


@app.route('/')
def index():
    """首页：显示环境变量检查 + 发送按钮"""
    from_email = os.environ.get('ALERT_FROM_EMAIL', '').strip()
    to_email = os.environ.get('ALERT_TO_EMAIL', '').strip()
    smtp_server = os.environ.get('ALERT_SMTP_SERVER', '').strip()
    smtp_port = os.environ.get('ALERT_SMTP_PORT', '').strip()
    password = os.environ.get('ALERT_EMAIL_PASSWORD', '').strip()

    items = [
        ('ALERT_FROM_EMAIL', from_email if from_email else '(未设置)', bool(from_email)),
        ('ALERT_TO_EMAIL', to_email if to_email else '(未设置)', bool(to_email)),
        ('ALERT_SMTP_SERVER', smtp_server if smtp_server else '(未设置)', bool(smtp_server)),
        ('ALERT_SMTP_PORT', smtp_port if smtp_port else '(未设置)', bool(smtp_port)),
        ('ALERT_EMAIL_PASSWORD', '已设置（长度 %d）' % len(password) if password else '(未设置)', bool(password)),
    ]

    rows = ''
    for k, v, ok in items:
        v_show = v if k == 'ALERT_SMTP_PORT' or k == 'ALERT_EMAIL_PASSWORD' else v[:30]
        icon = '✅' if ok else '❌'
        rows += '<div class="row"><span class="k">%s</span> %s <span class="v">%s</span></div>' % (k, icon, v_show)

    html = '''<!DOCTYPE html><html><head><meta charset="utf-8"><title>邮件测试</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{font-family:-apple-system,sans-serif;max-width:640px;margin:30px auto;padding:20px;background:#1e1b4b;color:#fff}
    h1{margin-bottom:8px}h2{margin:20px 0 12px 0;font-size:17px}
    .card{background:rgba(255,255,255,0.06);border-radius:14px;padding:20px;margin-bottom:20px;border:1px solid rgba(255,255,255,0.1)}
    button{background:#6366f1;color:#fff;border:none;padding:14px 28px;border-radius:10px;font-size:15px;cursor:pointer;font-weight:600}
    button:disabled{opacity:0.5;cursor:not-allowed}
    .row{padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:14px;display:flex;align-items:center}
    .k{color:#94a3b8;width:210px;flex-shrink:0}.v{word-break:break-all}
    #result{margin-top:16px;padding:16px;border-radius:10px;display:none;font-size:14px;line-height:1.7}
    .tip{background:rgba(99,102,241,0.15);padding:12px 16px;border-radius:10px;font-size:13px;color:#c7d2fe;margin-top:14px;line-height:1.6}
    .step{background:rgba(16,185,129,0.15);padding:12px 16px;border-radius:10px;font-size:13px;color:#34d399;margin-top:14px;line-height:1.6}
    </style></head><body>
    <h1>📧 Gmail 邮件测试</h1>
    <p style="color:#94a3b8;font-size:14px;margin-bottom:20px">用于验证 Render 环境变量 + Gmail SMTP 是否正常工作</p>

    <div class="card"><h2>① 环境变量检查</h2>''' + rows + '''
    <div class="tip">如果显示 ❌，请去 Render → Environment 检查变量是否已保存，然后去 Events 页面等它自动重新部署。</div>
    </div>

    <div class="card"><h2>② 发送测试邮件</h2>
    <button id="btn" onclick="sendMail()">📤 发送测试邮件</button>
    <div id="result"></div>
    </div>

    <div class="card"><h2>③ 常见问题</h2>
    <div style="font-size:14px;line-height:1.8;color:#e2e8f0">
    <p><b>Username and Password not accepted / 需要应用专用密码：</b><br>Gmail 的两步验证账号不能用登录密码。去 Google 账号 → 安全 → 两步验证 → 应用专用密码，生成一个 16 位密码填进来。</p>
    <p><b>Could not connect / Connection timed out：</b><br>SMTP 服务器地址或端口错误。Gmail 用 smtp.gmail.com，端口 465（SSL）或 587（STARTTLS）。</p>
    <p><b>Please log in with your web browser and then try again：</b><br>Google 拦截了登录，换一个应用专用密码即可。</p>
    </div></div>

    <script>
    function sendMail(){
        var btn=document.getElementById('btn');var r=document.getElementById('result');
        btn.disabled=true;btn.textContent='发送中...';
        r.style.display='block';r.style.background='rgba(251,191,36,0.15)';r.style.color='#fbbf24';r.innerHTML='⏳ 正在连接 Gmail SMTP 服务器（最多 30 秒）...';
        fetch('/send',{method:'POST'}).then(x=>x.json()).then(d=>{
            if(d.success){r.style.background='rgba(16,185,129,0.15)';r.style.color='#34d399';
            r.innerHTML='<b style="font-size:16px">✅ 发送成功！</b><br>'+d.message+'<div class="step">📱 现在打开手机 QQ 邮箱 APP，收件箱/垃圾箱里应该能看到测试邮件。<br>然后回你的主项目部署时，用同样的环境变量即可。</div>'}
            else{r.style.background='rgba(239,68,68,0.15)';r.style.color='#f87171';
            r.innerHTML='<b style="font-size:16px">❌ 失败</b><br>'+d.error+(d.detail?'<br><br><b>详情：</b><pre style="white-space:pre-wrap;background:rgba(0,0,0,0.3);padding:10px;border-radius:6px;margin-top:8px;font-size:12px">'+d.detail+'</pre>':'')}
            btn.disabled=false;btn.textContent='📤 发送测试邮件';
        }).catch(e=>{r.style.background='rgba(239,68,68,0.15)';r.style.color='#f87171';r.innerHTML='请求错误: '+e;btn.disabled=false;btn.textContent='📤 发送测试邮件'});
    }
    </script></body></html>
    '''
    return html, 200


@app.route('/send', methods=['POST'])
def send():
    """发邮件接口，返回 JSON 结果"""
    smtp_server = os.environ.get('ALERT_SMTP_SERVER', 'smtp.gmail.com').strip()
    from_addr = os.environ.get('ALERT_FROM_EMAIL', '').strip()
    to_addr = os.environ.get('ALERT_TO_EMAIL', '').strip()
    password = os.environ.get('ALERT_EMAIL_PASSWORD', '').strip()
    port_str = os.environ.get('ALERT_SMTP_PORT', '465').strip()

    if not from_addr or not to_addr or not password:
        return jsonify({'success': False, 'error': '环境变量不完整。需要：ALERT_FROM_EMAIL, ALERT_TO_EMAIL, ALERT_EMAIL_PASSWORD',
                       'detail': '当前读取到：ALERT_FROM_EMAIL=%s, ALERT_TO_EMAIL=%s, ALERT_SMTP_SERVER=%s, 密码长度=%d' % (
                           from_addr[:20] if from_addr else '(空)',
                           to_addr[:20] if to_addr else '(空)',
                           smtp_server[:20] if smtp_server else '(空)',
                           len(password))})

    try: smtp_port = int(port_str)
    except: smtp_port = 465

    try:
        msg = MIMEMultipart("alternative")
        msg['Subject'] = '[ETH EMA 预警] 测试邮件 · %s' % time.strftime('%H:%M:%S')
        msg['From'] = from_addr
        msg['To'] = to_addr
        body = '<html><body style="font-family:sans-serif;max-width:500px;margin:20px auto;padding:20px"><h2 style="color:#6366f1">✅ 邮件发送成功</h2><p>如果你看到这封邮件，说明 Gmail SMTP 配置完全正常，你的预警系统可以发邮件。</p><p>发送时间: %s</p><p>SMTP服务器: %s:%d</p><p>发件人: %s</p><p>收件人: %s</p></body></html>' % (
            time.strftime('%Y-%m-%d %H:%M:%S'), smtp_server, smtp_port, from_addr, to_addr)
        msg.attach(MIMEText(body, 'html', 'utf-8'))

        ctx = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL(smtp_server, smtp_port, context=ctx, timeout=25) as s:
                s.login(from_addr, password)
                s.sendmail(from_addr, [to_addr], msg.as_string())
            return jsonify({'success': True, 'message': '✅ SSL 465 发送成功！<br>收件人: <b>%s</b><br>请检查 QQ 邮箱收件箱（可能在「垃圾箱」或「广告邮件」里）。<br>现在回到你的主项目部署，用同样的环境变量即可。' % to_addr})
        except Exception as e1:
            err1 = str(e1)[:150]
            try:
                with smtplib.SMTP(smtp_server, 587, timeout=25) as s:
                    s.starttls(context=ctx)
                    s.login(from_addr, password)
                    s.sendmail(from_addr, [to_addr], msg.as_string())
                return jsonify({'success': True, 'message': '✅ STARTTLS 587 发送成功！<br>收件人: <b>%s</b><br>请检查 QQ 邮箱收件箱。' % to_addr})
            except Exception as e2:
                return jsonify({'success': False,
                                'error': '两次发送都失败了',
                                'detail': 'SSL 465 错误: %s\n\nSTARTTLS 587 错误: %s\n\n当前配置: server=%s, port=%d, from=%s, to=%s, 密码长度=%d' % (
                                    err1, str(e2)[:150], smtp_server, smtp_port, from_addr[:20], to_addr[:20], len(password))})
    except Exception as e:
        return jsonify({'success': False, 'error': '程序异常', 'detail': str(e)[:200]})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print('Gmail 邮件测试工具启动，访问 http://localhost:%d' % port)
    app.run(host='0.0.0.0', port=port, debug=False)

#!/usr/bin/env python3
"""邮件测试 - 同时试 Gmail SSL 465 / Gmail STARTTLS 587 / Outlook STARTTLS 587"""
from flask import Flask
import os, smtplib, ssl, time, socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)


def _row(label, value, ok=None):
    icon = '✅' if ok is True else ('❌' if ok is False else '·')
    return '<div class="row"><span class="k">%s</span><span class="icon">%s</span><span class="v">%s</span></div>' % (label, icon, str(value).replace('<', '&lt;'))


@app.route('/')
def index():
    from_email = os.environ.get('ALERT_FROM_EMAIL', '').strip()
    to_email = os.environ.get('ALERT_TO_EMAIL', '').strip()
    smtp_server = os.environ.get('ALERT_SMTP_SERVER', '').strip()
    smtp_port = os.environ.get('ALERT_SMTP_PORT', '').strip()
    password = os.environ.get('ALERT_EMAIL_PASSWORD', '').strip()

    rows = _row('ALERT_FROM_EMAIL', from_email, bool(from_email))
    rows += _row('ALERT_TO_EMAIL', to_email, bool(to_email))
    rows += _row('ALERT_SMTP_SERVER', smtp_server, bool(smtp_server))
    rows += _row('ALERT_SMTP_PORT', smtp_port, bool(smtp_port))
    rows += _row('ALERT_EMAIL_PASSWORD', '已设置（长度 %d）' % len(password), len(password) > 0)

    html = '''<!DOCTYPE html><html><head><meta charset="utf-8"><title>邮件测试</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{font-family:-apple-system,sans-serif;max-width:640px;margin:20px auto;padding:20px;background:#1e1b4b;color:#fff;line-height:1.7}
    h1{margin-bottom:8px}h2{margin:22px 0 14px;font-size:17px}
    .card{background:rgba(255,255,255,0.06);border-radius:14px;padding:18px 20px;margin-bottom:18px;border:1px solid rgba(255,255,255,0.1)}
    a.btn{display:inline-block;background:#6366f1;color:#fff;text-decoration:none;padding:14px 28px;border-radius:10px;font-size:15px;font-weight:600;margin-right:10px}
    .row{padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:14px;display:flex;align-items:center;flex-wrap:wrap}
    .k{color:#94a3b8;width:220px;flex-shrink:0}.icon{width:30px;text-align:center}.v{word-break:break-all;flex:1;color:#e2e8f0}
    .ok{background:rgba(16,185,129,0.15);color:#34d399}.fail{background:rgba(239,68,68,0.15);color:#f87171}
    .small{font-size:13px;color:#94a3b8;margin-top:8px;line-height:1.8}
    </style></head><body>
    <h1>📧 邮件发送测试</h1>
    <p style="color:#94a3b8;font-size:14px;margin-bottom:20px">自动试 3 种方式：Gmail SSL 465 → Gmail STARTTLS 587 → Outlook STARTTLS 587</p>

    <div class="card"><h2>① 环境变量检查</h2>''' + rows + '''
    <p class="small">有 ❌ 就去 Render → Environment 添加，保存后等自动重新部署。</p></div>

    <div class="card"><h2>② 发送测试邮件</h2>
    <a href="/send" class="btn">📤 点我发送</a>
    <p class="small">发送最多需要 45 秒（3 个尝试 × 15 秒），请耐心等待页面加载。</p></div>

    <div class="card"><h2>③ 重要提示</h2>
    <p class="small"><b>❗ Render 部署必须改 Start Command：</b><br>
    去 Render → Settings → Build &amp; Deploy → Start Command 改成：<br>
    <code style="background:rgba(0,0,0,0.3);padding:4px 8px;border-radius:4px">gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120</code><br>
    （加上 --timeout 120，不然 30 秒就会被 gunicorn 杀掉）</p>
    <p class="small"><b>Gmail 需要应用专用密码（16 位），不是登录密码。</b></p>
    <p class="small"><b>Outlook 备选方案：</b>注册一个 Outlook/Hotmail（免费），ALERT_FROM_EMAIL = xxx@outlook.com，密码 = 你的登录密码（或应用专用密码），SMTP_SERVER = smtp-mail.outlook.com，PORT = 587</p></div>

    </body></html>'''
    return html, 200


def _send_ssl(host, port, from_addr, password, to_addr, msg, timeout=15):
    """试 SMTP SSL 发送"""
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=ctx, timeout=timeout) as s:
        s.login(from_addr, password)
        s.sendmail(from_addr, [to_addr], msg.as_string())


def _send_starttls(host, port, from_addr, password, to_addr, msg, timeout=15):
    """试 SMTP STARTTLS 发送"""
    ctx = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=timeout) as s:
        s.starttls(context=ctx)
        s.login(from_addr, password)
        s.sendmail(from_addr, [to_addr], msg.as_string())


@app.route('/send')
def send():
    """按顺序试多种 SMTP 方式，全部返回 HTML 页面"""
    smtp_server = os.environ.get('ALERT_SMTP_SERVER', 'smtp.gmail.com').strip()
    from_addr = os.environ.get('ALERT_FROM_EMAIL', '').strip()
    to_addr = os.environ.get('ALERT_TO_EMAIL', '').strip()
    password = os.environ.get('ALERT_EMAIL_PASSWORD', '').strip()
    port_str = os.environ.get('ALERT_SMTP_PORT', '465').strip()

    head = '''<!DOCTYPE html><html><head><meta charset="utf-8"><title>发送结果</title>
    <meta name="viewport" content="width=device-width,initial-scale=1"><style>
    body{font-family:-apple-system,sans-serif;max-width:640px;margin:20px auto;padding:20px;background:#1e1b4b;color:#fff;line-height:1.7}
    .ok{background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);padding:20px;border-radius:14px;margin-bottom:20px;color:#34d399}
    .fail{background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);padding:20px;border-radius:14px;margin-bottom:20px;color:#f87171}
    h1{margin-bottom:8px}p{margin:8px 0}.small{font-size:13px;color:#94a3b8}
    pre{background:rgba(0,0,0,0.4);padding:14px;border-radius:8px;font-size:12px;white-space:pre-wrap;word-break:break-all;margin-top:10px;color:#cbd5e1}
    a{display:inline-block;background:#6366f1;color:#fff;text-decoration:none;padding:12px 22px;border-radius:10px;font-size:14px;font-weight:600;margin-top:16px;margin-right:10px}
    .attempt{padding:10px 14px;background:rgba(255,255,255,0.04);border-radius:8px;margin:8px 0;font-size:13px;color:#94a3b8}
    </style></head><body>'''

    if not from_addr or not to_addr or not password:
        return head + '<div class="fail"><h1>❌ 环境变量不完整</h1><p>需要在 Render → Environment 设置：<b>ALERT_FROM_EMAIL / ALERT_TO_EMAIL / ALERT_EMAIL_PASSWORD</b></p><p>当前读取：From=%s / To=%s / Server=%s / Port=%s / 密码长度=%d</p><a href="/">返回</a></div></body></html>' % (
            from_addr[:20] if from_addr else '(空)', to_addr[:20] if to_addr else '(空)',
            smtp_server[:20] if smtp_server else '(空)', port_str, len(password))

    try:
        smtp_port = int(port_str)
    except:
        smtp_port = 465

    # 构造邮件
    msg = MIMEMultipart("alternative")
    msg['Subject'] = '[ETH EMA 预警] 测试邮件 · %s' % time.strftime('%H:%M:%S')
    msg['From'] = from_addr
    msg['To'] = to_addr
    body = '''<html><body style="font-family:sans-serif;max-width:500px;margin:20px auto;padding:20px">
    <h2 style="color:#6366f1">✅ 测试邮件发送成功</h2>
    <p>发件人：%s</p><p>收件人：%s</p>
    <p>时间：%s</p></body></html>''' % (from_addr, to_addr, time.strftime('%Y-%m-%d %H:%M:%S'))
    msg.attach(MIMEText(body, 'html', 'utf-8'))

    # 准备要尝试的 SMTP 列表
    attempts = []

    # 判断是什么邮箱，选择对应策略
    is_gmail = '@gmail.com' in from_addr.lower()
    is_outlook = any(d in from_addr.lower() for d in ['@outlook.com', '@hotmail.com', '@live.com'])

    # Gmail 优先试 SSL 465，再试 STARTTLS 587
    if is_gmail:
        attempts.append(('Gmail SSL 465', 'smtp.gmail.com', 465, 'ssl'))
        attempts.append(('Gmail STARTTLS 587', 'smtp.gmail.com', 587, 'starttls'))
        attempts.append(('Outlook STARTTLS 587（备选）', 'smtp-mail.outlook.com', 587, 'starttls'))
    elif is_outlook:
        attempts.append(('Outlook STARTTLS 587', 'smtp-mail.outlook.com', 587, 'starttls'))
        attempts.append(('Gmail SSL 465（备选）', 'smtp.gmail.com', 465, 'ssl'))
        attempts.append(('Gmail STARTTLS 587（备选）', 'smtp.gmail.com', 587, 'starttls'))
    else:
        # 用户自定义 SMTP
        if smtp_port == 465:
            attempts.append(('自定义 SSL 465', smtp_server, 465, 'ssl'))
            attempts.append(('自定义 STARTTLS 587', smtp_server, 587, 'starttls'))
        else:
            attempts.append(('自定义 STARTTLS %d' % smtp_port, smtp_server, smtp_port, 'starttls'))
            attempts.append(('自定义 SSL 465', smtp_server, 465, 'ssl'))
        attempts.append(('Gmail SSL 465（备选）', 'smtp.gmail.com', 465, 'ssl'))

    errors_html = ''
    for name, host, port, mode in attempts:
        try:
            if mode == 'ssl':
                _send_ssl(host, port, from_addr, password, to_addr, msg, timeout=15)
            else:
                _send_starttls(host, port, from_addr, password, to_addr, msg, timeout=15)
            return head + '<div class="ok"><h1>✅ %s 发送成功！</h1><p>邮件已发送到：<b>%s</b></p><p>📱 请打开手机 QQ 邮箱 APP → 检查收件箱（没有就看「垃圾箱」「广告邮件」）。</p><p>配置：SMTP 服务器 %s，端口 %d，方式 %s</p>%s<a href="/">返回</a></div></body></html>' % (
                name, to_addr, host, port, mode.upper(),
                '<p class="small">下一步：在你的主项目 Render Environment 设置同样的变量，部署新版 web_app.py。</p>' if is_gmail or is_outlook else '')
        except socket.timeout:
            errors_html += '<div class="attempt">⏱ %s (%s:%d)：连接超时（Render 服务器连不上这个 SMTP）</div>' % (name, host, port)
        except Exception as e:
            err = str(e)[:250]
            errors_html += '<div class="attempt">❌ %s (%s:%d)：%s</div>' % (name, host, port, err)

    # 全部失败
    return head + '''<div class="fail"><h1>❌ 全部 SMTP 方式都失败了</h1>
    <p>以下是每个尝试的错误信息：</p>%s
    <p><b>当前配置：</b></p>
    <pre>发件人: %s
收件人: %s
密码长度: %d
自定义 SMTP: %s:%s</pre>
    <p class="small"><b>最可能的原因：</b></p>
    <p class="small"><b>1. Render 服务器被 Gmail SMTP 拦截（很常见）</b><br>
    → 换 Outlook 邮箱试试：注册 xxx@outlook.com（免费），ALERT_FROM_EMAIL 改成 Outlook 邮箱，密码用 Outlook 登录密码，SMTP_SERVER=smtp-mail.outlook.com，PORT=587</p>
    <p class="small"><b>2. Gmail 密码不是应用专用密码</b><br>
    → 开启两步验证后必须去 Google 账号 → 安全 → 应用专用密码 → 生成 16 位密码</p>
    <p class="small"><b>3. gunicorn timeout 太短（已经在 Start Command 加上 --timeout 120 了吗？）</b></p>
    <p class="small"><b>4. 终极方案：SendGrid</b><br>
    → 注册 sendgrid.com（免费每天 100 封），用 HTTP API 发邮件，绕开 SMTP 问题。这是云端发邮件最可靠的方式。</p>
    <a href="/">返回重试</a>
    </div></body></html>
    ''' % (errors_html, from_addr[:40], to_addr[:40], len(password), smtp_server, port_str)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print('邮件测试启动: http://localhost:%d' % port)
    app.run(host='0.0.0.0', port=port, debug=False)

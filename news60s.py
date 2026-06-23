"""
每日新闻早报 — 60s API 直发，零 LLM 零幻觉
数据源: 60s 读懂世界 (聚合全网新闻)
"""
import os
import sys
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta

MAIL_USER = os.getenv("MAIL_USER", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_TO = os.getenv("MAIL_TO") or MAIL_USER
SMTP_HOST = os.getenv("SMTP_HOST") or "smtp.gmail.com"
SMTP_PORT = int(os.getenv("SMTP_PORT") or "465")

BEIJING = timezone(timedelta(hours=8))
API = "https://60s.viki.moe/v2/60s"


def fetch_news(n=10):
    resp = requests.get(API, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    news_list = data.get("data", {}).get("news", [])
    return news_list[:n], data.get("data", {}).get("date", "")


def render_html(news_list, date_str):
    items = []
    for i, news in enumerate(news_list):
        num = "①②③④⑤⑥⑦⑧⑨⑩"[i] if i < 10 else str(i + 1)
        items.append(f'<tr><td style="vertical-align:top;padding:8px 10px 8px 0;color:#1a1a2e;font-weight:bold;font-size:16px;">{num}</td>'
                     f'<td style="vertical-align:top;padding:8px 0;font-size:14px;line-height:1.8;color:#333;">{news}</td></tr>')

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="max-width:680px;margin:0 auto;padding:20px;font-family:-apple-system,sans-serif;background:#fafafa;">
<div style="background:#fff;padding:24px 28px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.08);">
<h2 style="color:#1a1a2e;margin:0 0 4px;">📰 每日新闻早报 | {date_str}</h2>
<p style="color:#999;font-size:12px;margin:0 0 16px;">来源: 60s 读懂世界 · 聚合全网新闻</p>
<hr style="border:1px solid #eee;">
<table style="width:100%;border-collapse:collapse;">
{''.join(items)}
</table>
<hr style="border:1px solid #eee;margin-top:16px;">
<p style="color:#999;font-size:12px;">每日 UTC 00:10 自动推送 · 内容来自 60s API</p>
</div></body></html>"""


def send_email(html_body):
    msg = MIMEMultipart("alternative")
    today = datetime.now(BEIJING).strftime("%Y-%m-%d")
    msg["Subject"] = f"📰 每日新闻早报 | {today}"
    msg["From"] = MAIL_USER
    msg["To"] = MAIL_TO
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(MAIL_USER, MAIL_PASSWORD)
        server.sendmail(MAIL_USER, [MAIL_TO], msg.as_string())
    print(f"邮件已发送 → {MAIL_TO}")


def main():
    for var in ("MAIL_USER", "MAIL_PASSWORD"):
        if not os.getenv(var):
            sys.exit(f"缺少环境变量: {var}")

    print("1/2 获取新闻...")
    news, date_str = fetch_news()
    print(f"  获取到 {len(news)} 条新闻, 日期 {date_str}")

    print("2/2 发送邮件...")
    html = render_html(news, date_str)
    send_email(html)
    print("Done!")


if __name__ == "__main__":
    main()

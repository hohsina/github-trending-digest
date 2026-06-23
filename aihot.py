"""
AI 日报 — AI HOT API 直发，零 LLM 零幻觉
数据源: https://aihot.virxact.com
"""
import os
import sys
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
API_DAILY = "https://aihot.virxact.com/api/public/daily"
UA = "Mozilla/5.0 Chrome/124.0.0.0 Safari/537.36 aihot-skill/0.2.0"


def fetch_daily():
    resp = requests.get(API_DAILY, headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def build_html(data):
    today = datetime.now(BEIJING).strftime("%Y-%m-%d")
    date_str = data.get("date", today)
    lead = data.get("lead")
    sections = data.get("sections", [])

    parts = [f"""<h2 style="color:#1a1a2e;margin:0 0 4px;">🤖 AI 日报 | {date_str}</h2>
<p style="color:#999;font-size:12px;margin:0 0 16px;">来源: AI HOT (aihot.virxact.com) · 每日精选 AI 行业动态</p>
<hr style="border:1px solid #eee;">"""]

    if lead and lead.get("title"):
        parts.append(f'<p style="color:#555;font-size:14px;margin:12px 0;line-height:1.7;">📌 {lead["title"]}</p>')

    for section in sections:
        label = section.get("label", "")
        items = section.get("items", [])
        if not items:
            continue
        parts.append(f'<h3 style="color:#1a1a2e;margin:20px 0 8px;border-left:4px solid #3498db;padding-left:10px;">{label}</h3>')
        for item in items:
            title = item.get("title", "")
            summary = item.get("summary", "")
            url = item.get("sourceUrl", "")
            source = item.get("sourceName", "")
            url_html = f' <a href="{url}" style="color:#3498db;font-size:12px;">[链接]</a>' if url else ""
            source_html = f' <span style="color:#999;font-size:11px;">({source})</span>' if source else ""
            parts.append(f"""<div style="margin:10px 0 14px;padding:10px 14px;background:#f8f9fa;border-radius:6px;">
<p style="margin:0 0 4px;font-weight:bold;font-size:14px;color:#1a1a2e;">{title}{url_html}{source_html}</p>
<p style="margin:0;font-size:13px;line-height:1.7;color:#555;">{summary[:400]}{'…' if len(summary) > 400 else ''}</p>
</div>""")

    parts.append(f"""<br><hr style="border:1px solid #eee;">
<p style="color:#999;font-size:12px;">每日 UTC 00:30 自动推送 · 数据来自 AI HOT API</p>""")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="max-width:720px;margin:0 auto;padding:20px;font-family:-apple-system,sans-serif;background:#fafafa;">
<div style="background:#fff;padding:24px 28px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.08);">
{''.join(parts)}
</div></body></html>"""


def send_email(html_body):
    msg = MIMEMultipart("alternative")
    today = datetime.now(BEIJING).strftime("%Y-%m-%d")
    msg["Subject"] = f"🤖 AI 日报 | {today}"
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

    print("1/2 获取 AI 日报...")
    data = fetch_daily()
    sections_count = len(data.get("sections", []))
    items_count = sum(len(s.get("items", [])) for s in data.get("sections", []))
    print(f"  {sections_count} 个板块, {items_count} 条资讯")

    print("2/2 发送邮件...")
    html = build_html(data)
    send_email(html)
    print("Done!")


if __name__ == "__main__":
    main()

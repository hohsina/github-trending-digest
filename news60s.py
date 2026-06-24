"""
每日新闻早报 — 60s 简报 + 头条 + 微博 + 抖音，一封信四份内容，零 LLM 零幻觉
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
API_60S = "https://60s.viki.moe/v2/60s"
API_TOUTIAO = "https://60s.viki.moe/v2/toutiao"
API_WEIBO = "https://60s.viki.moe/v2/weibo"
API_DOUYIN = "https://60s.viki.moe/v2/douyin"

NUMS = "①②③④⑤⑥⑦⑧⑨⑩"


def fetch_60s(n=10):
    resp = requests.get(API_60S, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    news = data.get("data", {}).get("news", [])
    date_str = data.get("data", {}).get("date", "")
    return news[:n], date_str


def fetch_toutiao(n=10):
    resp = requests.get(API_TOUTIAO, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data", [])[:n]
    return [{"title": i["title"], "hot": i.get("hot_value", 0), "url": i.get("link", "")}
            for i in items]


def fetch_weibo(n=10):
    resp = requests.get(API_WEIBO, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data", [])[:n]
    return [{"title": i["title"], "hot": i.get("hot_value", 0), "url": i.get("link", "")}
            for i in items]


def fetch_douyin(n=10):
    resp = requests.get(API_DOUYIN, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data", [])[:n]
    return [{"title": i["title"], "hot": i.get("hot_value", 0), "url": i.get("link", "")}
            for i in items]


def build_html(news60s, date_str, toutiao, weibo, douyin):
    today = datetime.now(BEIJING).strftime("%Y-%m-%d")

    # ── 60s 简报部分 ──
    parts = [f"""<h2 style="color:#1a1a2e;margin:0 0 4px;">📰 每日新闻早报 | {today}</h2>
<p style="color:#999;font-size:12px;margin:0 0 16px;">来源: 60s 读懂世界 · 聚合全网权威新闻</p>
<hr style="border:1px solid #eee;">
<table style="width:100%;border-collapse:collapse;">"""]
    for i, n in enumerate(news60s):
        num = NUMS[i] if i < 10 else str(i + 1)
        parts.append(
            f'<tr><td style="vertical-align:top;padding:8px 10px 8px 0;color:#1a1a2e;font-weight:bold;font-size:16px;">{num}</td>'
            f'<td style="vertical-align:top;padding:8px 0;font-size:14px;line-height:1.8;color:#333;">{n}</td></tr>')
    parts.append("</table>")

    # ── 头条热榜部分 ──
    parts.append(f"""<br><br>
<hr style="border:2px solid #1a1a2e;">
<h2 style="color:#1a1a2e;margin:16px 0 4px;">🔥 今日头条热榜 Top 10</h2>
<p style="color:#999;font-size:12px;margin:0 0 16px;">来源: 今日头条 · 实时热搜</p>
<hr style="border:1px solid #eee;">
<table style="width:100%;border-collapse:collapse;">""")
    for i, t in enumerate(toutiao):
        num = NUMS[i] if i < 10 else str(i + 1)
        hot_str = f"{t['hot'] / 10000:.0f}万" if t['hot'] >= 10000 else str(t['hot'])
        url_html = f'<br><a href="{t["url"]}" style="color:#3498db;font-size:12px;">{t["url"]}</a>' if t["url"] else ""
        parts.append(
            f'<tr><td style="vertical-align:top;padding:8px 10px 8px 0;color:#1a1a2e;font-weight:bold;font-size:16px;">{num}</td>'
            f'<td style="vertical-align:top;padding:8px 0;font-size:14px;line-height:1.6;color:#333;">'
            f'{t["title"]} <span style="color:#e67e22;font-size:12px;">🔥{hot_str}</span>{url_html}</td></tr>')
    parts.append("</table>")

    # ── 微博热搜部分 ──
    parts.append(f"""<br><br>
<hr style="border:2px solid #e0245e;">
<h2 style="color:#e0245e;margin:16px 0 4px;">🔥 微博热搜 Top 10</h2>
<p style="color:#999;font-size:12px;margin:0 0 16px;">来源: 微博 · 实时热搜</p>
<hr style="border:1px solid #eee;">
<table style="width:100%;border-collapse:collapse;">""")
    for i, w in enumerate(weibo):
        num = NUMS[i] if i < 10 else str(i + 1)
        hot_str = f"{w['hot'] / 10000:.0f}万" if w['hot'] >= 10000 else str(w['hot'])
        url_html = f'<br><a href="{w["url"]}" style="color:#e0245e;font-size:12px;">{w["url"]}</a>' if w["url"] else ""
        parts.append(
            f'<tr><td style="vertical-align:top;padding:8px 10px 8px 0;color:#e0245e;font-weight:bold;font-size:16px;">{num}</td>'
            f'<td style="vertical-align:top;padding:8px 0;font-size:14px;line-height:1.6;color:#333;">'
            f'{w["title"]} <span style="color:#e0245e;font-size:12px;">🔥{hot_str}</span>{url_html}</td></tr>')
    parts.append("</table>")

    # ── 抖音热搜部分 ──
    parts.append(f"""<br><br>
<hr style="border:2px solid #010101;">
<h2 style="color:#010101;margin:16px 0 4px;">🎵 抖音热搜 Top 10</h2>
<p style="color:#999;font-size:12px;margin:0 0 16px;">来源: 抖音 · 实时热搜</p>
<hr style="border:1px solid #eee;">
<table style="width:100%;border-collapse:collapse;">""")
    for i, dy in enumerate(douyin):
        num = NUMS[i] if i < 10 else str(i + 1)
        hot_str = f"{dy['hot'] / 10000:.0f}万" if dy['hot'] >= 10000 else str(dy['hot'])
        parts.append(
            f'<tr><td style="vertical-align:top;padding:8px 10px 8px 0;color:#010101;font-weight:bold;font-size:16px;">{num}</td>'
            f'<td style="vertical-align:top;padding:8px 0;font-size:14px;line-height:1.6;color:#333;">'
            f'{dy["title"]} <span style="color:#010101;font-size:12px;">🔥{hot_str}</span></td></tr>')
    parts.append("</table>")

    # ── 页脚 ──
    parts.append(f"""<br>
<hr style="border:1px solid #eee;">
<p style="color:#999;font-size:12px;">每日 UTC 00:09 自动推送 · 60s 简报 &amp; 头条 &amp; 微博 &amp; 抖音</p>""")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="max-width:720px;margin:0 auto;padding:20px;font-family:-apple-system,sans-serif;background:#fafafa;">
<div style="background:#fff;padding:24px 28px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.08);">
{''.join(parts)}
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

    print("1/5 获取 60s 新闻简报...")
    news60s, date_str = fetch_60s()
    print(f"  {len(news60s)} 条, 日期 {date_str}")

    print("2/5 获取头条热榜...")
    toutiao = fetch_toutiao()
    print(f"  {len(toutiao)} 条")

    print("3/5 获取微博热搜...")
    weibo = fetch_weibo()
    print(f"  {len(weibo)} 条")

    print("4/5 获取抖音热搜...")
    douyin = fetch_douyin()
    print(f"  {len(douyin)} 条")

    print("5/5 发送邮件...")
    html = build_html(news60s, date_str, toutiao, weibo, douyin)
    send_email(html)
    print("Done!")


if __name__ == "__main__":
    main()

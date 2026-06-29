"""
每日新闻早报 — 60s 简报 + 头条 + 微博 + 抖音 + 知乎 + 百度 + 小红书
一封信七份内容，零 LLM 零幻觉
"""
import os
import sys
import time
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta


def _get(url, timeout=15, retries=3):
    """带重试和延迟的 GET，防止 429 限流"""
    for attempt in range(retries):
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 429:
            wait = (attempt + 1) * 3
            print(f"  429 限流，{wait}s 后重试...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        time.sleep(0.5)  # 请求间隔，避免连续轰炸 API
        return resp
    resp.raise_for_status()
    return resp

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
API_ZHIHU = "https://60s.viki.moe/v2/zhihu"
API_BAIDU = "https://60s.viki.moe/v2/baidu/hot"
API_REDNOTE = "https://60s.viki.moe/v2/rednote"

NUMS = "①②③④⑤⑥⑦⑧⑨⑩"


def fetch_60s(n=10):
    resp = _get(API_60S, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    news = data.get("data", {}).get("news", [])
    date_str = data.get("data", {}).get("date", "")
    return news[:n], date_str


def fetch_toutiao(n=10):
    resp = _get(API_TOUTIAO, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data", [])[:n]
    return [{"title": i["title"], "hot": i.get("hot_value", 0), "url": i.get("link", "")}
            for i in items]


def fetch_weibo(n=10):
    resp = _get(API_WEIBO, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data", [])[:n]
    return [{"title": i["title"], "hot": i.get("hot_value", 0), "url": i.get("link", "")}
            for i in items]


def fetch_douyin(n=10):
    resp = _get(API_DOUYIN, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data", [])[:n]
    return [{"title": i["title"], "hot": i.get("hot_value", 0), "url": i.get("link", "")}
            for i in items]


def fetch_zhihu(n=10):
    resp = _get(API_ZHIHU, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data", [])[:n]
    return [{"title": i["title"], "hot_desc": i.get("hot_value_desc", ""), "url": i.get("link", "")}
            for i in items]


def fetch_baidu(n=10):
    resp = _get(API_BAIDU, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data", [])[:n]
    return [{"title": i["title"], "hot_desc": i.get("score_desc", ""), "url": i.get("url", "")}
            for i in items]


def fetch_rednote(n=10):
    resp = _get(API_REDNOTE, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data", [])[:n]
    return [{"title": i["title"], "hot_desc": str(i.get("score", "")), "url": i.get("link", "")}
            for i in items]


def _section(name, color, icon, items, show_hot=True):
    parts = [f"""<br><br>
<hr style="border:2px solid {color};">
<h2 style="color:{color};margin:16px 0 4px;">{icon} {name} Top 10</h2>
<p style="color:#999;font-size:12px;margin:0 0 16px;">来源: 60s API · 实时热搜</p>
<hr style="border:1px solid #eee;">
<table style="width:100%;border-collapse:collapse;">"""]
    for i, item in enumerate(items):
        num = NUMS[i] if i < 10 else str(i + 1)
        hot_html = f' <span style="color:{color};font-size:12px;">🔥{item.get("hot_desc") or item.get("hot", "")}</span>' if show_hot and (item.get("hot_desc") or item.get("hot")) else ""
        url_html = f'<br><a href="{item["url"]}" style="color:{color};font-size:12px;">{item["url"]}</a>' if item.get("url") else ""
        parts.append(
            f'<tr><td style="vertical-align:top;padding:8px 10px 8px 0;color:{color};font-weight:bold;font-size:16px;">{num}</td>'
            f'<td style="vertical-align:top;padding:8px 0;font-size:14px;line-height:1.6;color:#333;">'
            f'{item["title"]}{hot_html}{url_html}</td></tr>')
    parts.append("</table>")
    return "\n".join(parts)


def build_html(news60s, date_str, toutiao, weibo, douyin, zhihu, baidu_hot, rednote):
    today = datetime.now(BEIJING).strftime("%Y-%m-%d")

    parts = [f"""<h2 style="color:#1a1a2e;margin:0 0 4px;">📰 每日新闻早报 | {today}</h2>
<p style="color:#999;font-size:12px;margin:0 0 16px;">聚合全网权威新闻与热搜</p>
<hr style="border:1px solid #eee;">
<table style="width:100%;border-collapse:collapse;">"""]
    for i, n in enumerate(news60s):
        num = NUMS[i] if i < 10 else str(i + 1)
        parts.append(
            f'<tr><td style="vertical-align:top;padding:8px 10px 8px 0;color:#1a1a2e;font-weight:bold;font-size:16px;">{num}</td>'
            f'<td style="vertical-align:top;padding:8px 0;font-size:14px;line-height:1.8;color:#333;">{n}</td></tr>')
    parts.append("</table>")

    parts.append(_section("今日头条热榜", "#1a1a2e", "🔥", toutiao))
    parts.append(_section("微博热搜", "#e0245e", "🔥", weibo))
    parts.append(_section("抖音热搜", "#010101", "🎵", douyin))
    parts.append(_section("知乎热搜", "#1772f0", "💡", zhihu))
    parts.append(_section("百度热搜", "#4e6ef2", "🔍", baidu_hot))
    parts.append(_section("小红书热搜", "#ff2442", "📕", rednote))

    parts.append(f"""<br>
<hr style="border:1px solid #eee;">
<p style="color:#999;font-size:12px;">每日 UTC 00:09 自动推送 · 60s 简报 &amp; 7 大热榜</p>""")

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

    print("1/8 获取 60s 新闻简报...")
    news60s, date_str = fetch_60s()
    print(f"  {len(news60s)} 条, 日期 {date_str}")

    print("2/8 获取头条热榜...")
    toutiao = fetch_toutiao()
    print(f"  {len(toutiao)} 条")

    print("3/8 获取微博热搜...")
    weibo = fetch_weibo()
    print(f"  {len(weibo)} 条")

    print("4/8 获取抖音热搜...")
    douyin = fetch_douyin()
    print(f"  {len(douyin)} 条")

    print("5/8 获取知乎热搜...")
    zhihu = fetch_zhihu()
    print(f"  {len(zhihu)} 条")

    print("6/8 获取百度热搜...")
    baidu_hot = fetch_baidu()
    print(f"  {len(baidu_hot)} 条")

    print("7/8 获取小红书热搜...")
    rednote = fetch_rednote()
    print(f"  {len(rednote)} 条")

    print("8/8 发送邮件...")
    html = build_html(news60s, date_str, toutiao, weibo, douyin, zhihu, baidu_hot, rednote)
    send_email(html)
    print("Done!")


if __name__ == "__main__":
    main()

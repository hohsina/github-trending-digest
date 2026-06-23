"""
国内热点新闻日报 — 60s API + LLM 润色 + 邮件推送
数据源: 今日头条热榜 (60s API)
"""
import os
import sys
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta

# ── 配置 ──
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or "https://apihub.agnes-ai.com/v1"
LLM_MODEL = os.getenv("LLM_MODEL") or "agnes-2.0-flash"
MAIL_USER = os.getenv("MAIL_USER", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_TO = os.getenv("MAIL_TO") or MAIL_USER
SMTP_HOST = os.getenv("SMTP_HOST") or "smtp.gmail.com"
SMTP_PORT = int(os.getenv("SMTP_PORT") or "465")

BEIJING = timezone(timedelta(hours=8))
NEWS_API = "https://60s.viki.moe/v2/toutiao"


def fetch_news(n=10):
    """从 60s API 获取今日头条热榜 Top N."""
    resp = requests.get(NEWS_API, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data", [])[:n]
    return [
        {
            "title": item["title"],
            "hot": item.get("hot_value", 0),
            "url": item.get("link", ""),
        }
        for item in items
    ]


def call_llm(prompt):
    """调用 LLM 生成日报，失败无限重试."""
    import time as _time
    headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 4096,
    }
    attempt = 0
    while True:
        attempt += 1
        resp = requests.post(f"{LLM_BASE_URL}/chat/completions", json=payload,
                             headers=headers, timeout=120)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        if resp.status_code == 400:
            raise RuntimeError(f"LLM API error 400: {resp.text[:500]}")
        delay = min(attempt * 60, 300)
        print(f"  LLM {resp.status_code}, {delay}s 后重试 (第 {attempt} 次)...")
        _time.sleep(delay)


def build_prompt(news_list):
    """构造简洁格式 prompt."""
    today = datetime.now(BEIJING).strftime("%Y-%m-%d")
    data = json.dumps(news_list, ensure_ascii=False, indent=2)

    return f"""你是新闻编辑。根据以下今日头条热榜数据撰写一份简洁的国内热点新闻日报。

【规则】
1. 只输出提供的 {len(news_list)} 条新闻，不添加、不遗漏
2. 每条输出：标题 + 一句话概括 + 热度指数
3. 标题保持原标题不变
4. 开头写一句当日要闻概括
5. 简洁，不要啰嗦点评

【输出格式】

📰 国内热点新闻日报 | {today}
━━━━━━━━━━━━━━━━━━━━━━
今日要闻：[一句话概括]

---
[依次输出全部 {len(news_list)} 条]

① {{原标题}} 🔥{{热度}}
📝 {{一句话概括}}

---
━━━━━━━━━━━━━━━━━━━━━━
📡 数据来源: 今日头条热榜 · 每日自动生成

【数据】
{data}"""


def render_html(text):
    """纯文本 → HTML 邮件."""
    lines = text.split("\n")
    body_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            body_lines.append("<br>")
        elif line.startswith("📰"):
            body_lines.append(f'<h2 style="color:#1a1a2e;">{line[2:]}</h2>')
        elif line.startswith("━━"):
            body_lines.append('<hr style="border:1px solid #eee;">')
        elif line.startswith("📡"):
            body_lines.append(f'<p style="color:#999;font-size:12px;">{line[2:]}</p>')
        elif line.startswith("今日要闻"):
            body_lines.append(f'<p style="color:#555;font-size:14px;margin:8px 0;">{line}</p>')
        elif line.startswith("①") or line.startswith("②") or line.startswith("③") or line.startswith("④") or line.startswith("⑤") or line.startswith("⑥") or line.startswith("⑦") or line.startswith("⑧") or line.startswith("⑨") or line.startswith("⑩"):
            body_lines.append(f'<h3 style="margin:16px 0 4px;color:#1a1a2e;">{line}</h3>')
        elif line.startswith("📝"):
            body_lines.append(f'<p style="margin:2px 0 8px 16px;color:#333;font-size:14px;">{line}</p>')
        else:
            body_lines.append(f'<p style="margin:2px 0;color:#333;font-size:14px;">{line}</p>')
    body = "\n".join(body_lines)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="max-width:680px;margin:0 auto;padding:20px;font-family:-apple-system,sans-serif;background:#fafafa;">
<div style="background:#fff;padding:24px 28px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.08);">
{body}
</div></body></html>"""


def send_email(html_body):
    """发送邮件."""
    msg = MIMEMultipart("alternative")
    today = datetime.now(BEIJING).strftime("%Y-%m-%d")
    msg["Subject"] = f"📰 国内热点新闻日报 | {today}"
    msg["From"] = MAIL_USER
    msg["To"] = MAIL_TO
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(MAIL_USER, MAIL_PASSWORD)
        server.sendmail(MAIL_USER, [MAIL_TO], msg.as_string())
    print(f"邮件已发送 → {MAIL_TO}")


def main():
    for var in ("LLM_API_KEY", "MAIL_USER", "MAIL_PASSWORD"):
        if not os.getenv(var):
            sys.exit(f"缺少环境变量: {var}")

    print("1/3 获取头条热榜...")
    news = fetch_news()
    print(f"  获取到 {len(news)} 条新闻")

    print("2/3 生成日报...")
    prompt = build_prompt(news)
    result = call_llm(prompt)

    print("3/3 发送邮件...")
    html = render_html(result)
    send_email(html)
    print("Done!")


if __name__ == "__main__":
    main()

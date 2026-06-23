"""
GitHub Trending 日报 — 抓取 + Gemini 分析 + 邮件推送
永久免费：GitHub Actions (免费) + Gemini API (永久免费层) + Gmail (免费)
"""
import os
import sys
import json
import base64
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

# ── 配置（全部从环境变量读取） ──
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
MAIL_USER = os.getenv("MAIL_USER", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_TO = os.getenv("MAIL_TO") or MAIL_USER
GEMINI_MODEL = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
# SMTP 默认 Gmail，QQ邮箱设 SMTP_HOST=smtp.qq.com
SMTP_HOST = os.getenv("SMTP_HOST") or "smtp.gmail.com"
SMTP_PORT = int(os.getenv("SMTP_PORT") or "465")

BEIJING = timezone(timedelta(hours=8))


def scrape_trending(n=10):
    """抓取 GitHub Trending 日榜 Top N."""
    url = "https://github.com/trending?since=daily"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    repos = []
    articles = soup.find_all("article", class_="Box-row")[:n]
    for art in articles:
        h2 = art.find("h2")
        if not h2:
            continue
        a_tag = h2.find("a")
        if not a_tag:
            continue
        repo_path = a_tag.get("href", "").strip().lstrip("/")

        desc_tag = art.find("p", class_="col-9")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        lang_tag = art.find("span", itemprop="programmingLanguage")
        language = lang_tag.get_text(strip=True) if lang_tag else "Unknown"

        # 总星数
        stars_elem = art.select_one("a.Link--muted")
        total_stars = stars_elem.get_text(strip=True).replace(",", "") if stars_elem else "?"

        # 今日新增星数
        today_elem = art.select_one("span.d-inline-block.float-sm-right")
        today_stars = today_elem.get_text(strip=True).split()[0] if today_elem else "?"

        repos.append({
            "name": repo_path,
            "url": f"https://github.com/{repo_path}",
            "description": description,
            "language": language,
            "total_stars": total_stars,
            "today_stars": today_stars,
            "readme": "",
        })
    return repos


def fetch_readme(repo_name):
    """获取仓库 README 前 2000 字符作为事实锚点."""
    url = f"https://api.github.com/repos/{repo_name}/readme"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            content_b64 = resp.json().get("content", "")
            text = base64.b64decode(content_b64).decode("utf-8", errors="ignore")
            return text[:2000]
    except Exception:
        pass
    return ""


def call_gemini(prompt):
    """调用 Gemini API 生成日报，自动重试瞬时故障."""
    import time as _time
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
    }
    for attempt in range(3):
        resp = requests.post(url, json=payload, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        if resp.status_code >= 500:
            print(f"  Gemini {resp.status_code}, retry {attempt + 1}/3...")
            _time.sleep(2 ** attempt)
            continue
        raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text[:500]}")
    raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text[:500]}")


def build_prompt(repos):
    """构造防幻觉 prompt."""
    today = datetime.now(BEIJING).strftime("%Y-%m-%d")
    repos_json = json.dumps(repos, ensure_ascii=False, indent=2)

    template = """你是资深开源技术主编。根据以下 JSON 数据撰写今日 GitHub Trending 日报。

【严格约束】
1. 项目简介和点评必须 100% 基于提供的 readme 和 description，禁止使用预训练知识编造
2. 如果 readme 提到 Beta/Experimental/WIP，必须在点评中指出成熟度风险
3. Star 数使用 JSON 中的精确数字，禁止用"数百""近千"等模糊词
4. 每项控制在 3-5 行，点评要毒辣、说人话

【输出格式 — 严格按此模板】

📰 GitHub Trending 日报 | {today}
━━━━━━━━━━━━━━━━━━━━━━
今日看点：[一句话总结今日榜单趋势]

---
[依次输出 1-10，格式如下]

### ① {{项目名}}
⭐ {{总星数}} · 今日 +{{今日新增}} · {{语言}}
🔗 {{链接}}
📝 {{一句话简介}}
💬 {{点评}}

---
━━━━━━━━━━━━━━━━━━━━━━
📡 数据来源: github.com/trending · 每日 UTC 00:00 自动生成

【输入数据】
{repos_json}"""
    return template.replace("{today}", today).replace("{repos_json}", repos_json)


def render_html(markdown_text):
    """Markdown → 简洁 HTML 邮件."""
    # 简单手写转换，不引入额外依赖
    lines = markdown_text.split("\n")
    html_lines = []
    in_para = False

    for line in lines:
        if line.startswith("### "):
            if in_para:
                html_lines.append("</p>")
                in_para = False
            html_lines.append(f'<h3 style="margin:20px 0 4px;color:#1a1a2e;">{line[4:]}</h3>')
        elif line.startswith("📰 "):
            html_lines.append(f'<h1 style="color:#1a1a2e;font-size:20px;margin:0 0 4px;">{line[2:]}</h1>')
        elif line.startswith("━━"):
            html_lines.append('<hr style="border:1px solid #e0e0e0;margin:12px 0;">')
        elif line.startswith("⭐ ") or line.startswith("🔗 ") or line.startswith("📝 ") or line.startswith("💬 ") or line.startswith("📡 "):
            if in_para:
                html_lines.append("</p>")
                in_para = False
            html_lines.append(f'<p style="margin:2px 0;color:#333;font-size:14px;line-height:1.7;">{line}</p>')
        elif line.strip():
            if not in_para:
                html_lines.append('<p style="margin:2px 0;color:#333;font-size:14px;line-height:1.7;">')
                in_para = True
            html_lines.append(line + "<br>")
        else:
            if in_para:
                html_lines.append("</p>")
                in_para = False

    if in_para:
        html_lines.append("</p>")

    body = "\n".join(html_lines)
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="max-width:680px;margin:0 auto;padding:20px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;background:#fafafa;">
<div style="background:#fff;padding:24px 28px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.08);">
{body}
</div>
</body>
</html>"""


def send_email(html_body):
    """通过 SMTP 发送邮件（默认 Gmail，支持 QQ 邮箱）."""
    msg = MIMEMultipart("alternative")
    today = datetime.now(BEIJING).strftime("%Y-%m-%d")
    msg["Subject"] = f"📰 GitHub Trending 日报 | {today}"
    msg["From"] = MAIL_USER
    msg["To"] = MAIL_TO
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(MAIL_USER, MAIL_PASSWORD)
        server.sendmail(MAIL_USER, [MAIL_TO], msg.as_string())
    print(f"邮件已发送 → {MAIL_TO}")


def main():
    errors = []
    for var in ("GEMINI_API_KEY", "MAIL_USER", "MAIL_PASSWORD"):
        if not os.getenv(var):
            errors.append(f"缺少环境变量: {var}")
    if errors:
        sys.exit("\n".join(errors))

    print("1/4 抓取 GitHub Trending...")
    repos = scrape_trending()

    print("2/4 获取 README...")
    for i, r in enumerate(repos):
        print(f"  [{i+1}/{len(repos)}] {r['name']}")
        r["readme"] = fetch_readme(r["name"])

    print("3/4 调用 Gemini 生成日报...")
    prompt = build_prompt(repos)
    newsletter = call_gemini(prompt)

    print("4/4 发送邮件...")
    html = render_html(newsletter)
    send_email(html)

    print("Done!")


if __name__ == "__main__":
    main()

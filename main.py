"""
GitHub Trending 日报 — 抓取 + LLM 分析 + 邮件推送
永久免费：GitHub Actions (免费) + Agnes AI (免费) + 邮箱 SMTP (免费)
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
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or "https://apihub.agnes-ai.com/v1"
LLM_MODEL = os.getenv("LLM_MODEL") or "agnes-2.0-flash"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
MAIL_USER = os.getenv("MAIL_USER", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_TO = os.getenv("MAIL_TO") or MAIL_USER
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
    articles = soup.find_all("article", class_="Box-row")
    if len(articles) < n:
        # fallback: newer GitHub layout
        articles = soup.select('[class*="Box-row"]')
    for art in articles[:n]:
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
            return text[:800]
    except Exception:
        pass
    return ""


def call_llm(prompt):
    """调用 LLM (OpenAI 兼容) 生成日报，失败自动重试直到成功."""
    import time as _time
    url = f"{LLM_BASE_URL}/chat/completions"
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 8192,
    }
    headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}
    attempt = 0
    while True:
        attempt += 1
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        if resp.status_code == 400:
            raise RuntimeError(f"LLM API error {resp.status_code}: {resp.text[:500]}")
        delay = min(attempt * 60, 300)  # 渐进：60s → 120s → 180s → 240s → 300s (封顶)
        print(f"  LLM {resp.status_code}, {delay}s 后重试 (第 {attempt} 次)...")
        _time.sleep(delay)


def build_prompt(repos):
    """构造防幻觉 prompt."""
    today = datetime.now(BEIJING).strftime("%Y-%m-%d")
    repos_json = json.dumps(repos, ensure_ascii=False, indent=2)

    template = """你是技术编辑。根据以下 JSON 数据撰写今日 GitHub Trending 日报。JSON 中的每一项都对应一个真实仓库。

【最高优先级 — 违反即为失败】
1. 只输出 JSON 中存在的仓库，一个不多一个不少。不允许从预训练记忆中补充任何仓库。
2. 所有数字（Star、技能数、版本号等）必须与 JSON 或 readme 原文逐字一致。禁止四舍五入、禁止改写、禁止用约数。
3. readme 中提到的许可证名称必须原文照抄（如 MIT、Apache 2.0、AGPLv3）。readme 没提许可证就不准写许可证。
4. 技能数、工具数等关键指标必须从 readme 中精确引用，不得自行计算或改写。

【次优先级】
5. 简介和点评基于 readme + description，不得编造项目背景、商业故事、竞品对比
6. readme 提到 Beta/Experimental/WIP 的，点评中必须指出成熟度风险
7. Star 数用 JSON 中的精确值，不用"数百""近千"等模糊词
8. 每条点评 2-3 句，说人话，不要啰嗦

【输出格式】

📰 GitHub Trending 日报 | {today}
━━━━━━━━━━━━━━━━━━━━━━
今日看点：[一句话总结今日榜单趋势]

---
[依次输出全部 10 个仓库]

### ① {{项目名}}
⭐ {{总星数}} · 今日 +{{今日新增}} · {{语言}}
🔗 {{链接}}
📝 {{一句话简介（基于 readme）}}
💬 {{点评（基于 readme 事实）}}

---
━━━━━━━━━━━━━━━━━━━━━━
📡 数据来源: github.com/trending · 每日自动生成

【输入 JSON 数据 — 以下每个仓库都必须出现在输出中】
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
    for var in ("LLM_API_KEY", "MAIL_USER", "MAIL_PASSWORD"):
        if not os.getenv(var):
            errors.append(f"缺少环境变量: {var}")
    if errors:
        sys.exit("\n".join(errors))

    print("1/4 抓取 GitHub Trending...")
    repos = scrape_trending()
    print(f"  获取到 {len(repos)} 个仓库")

    print("2/4 获取 README...")
    for i, r in enumerate(repos):
        print(f"  [{i+1}/{len(repos)}] {r['name']}")
        r["readme"] = fetch_readme(r["name"])

    print("3/4 调用 LLM 生成日报...")
    prompt = build_prompt(repos)
    newsletter = call_llm(prompt)

    print("4/4 发送邮件...")
    html = render_html(newsletter)
    send_email(html)

    print("Done!")


if __name__ == "__main__":
    main()

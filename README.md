# GitHub Trending 日报

每天早 8 点自动推送 GitHub Trending Top 10 到邮箱，Gemini AI 深度分析。

**永久免费**：GitHub Actions (免费) + Gemini API (永久免费层 1500次/天) + 邮箱 SMTP (免费)

## 部署 (3 步)

### 1. 获取密钥

| 密钥 | 获取方式 |
|------|---------|
| Gemini API Key | [aistudio.google.com](https://aistudio.google.com) → Get API Key，免费无需绑卡 |
| 邮箱 | Gmail 或 QQ 邮箱均可 |
| 邮箱授权码 | **Gmail**: 账号 → 安全 → 两步验证 → App Password → Mail/Other |
|  | **QQ 邮箱**: 设置 → 账户 → POP3/SMTP 服务 → 开启 → 生成授权码 |

### 2. Fork 并配置 Secrets

Fork 本仓库，在 Settings → Secrets and variables → Actions 添加：

**必填：**

| Secret | 说明 |
|--------|------|
| `GEMINI_API_KEY` | Gemini API Key |
| `MAIL_USER` | 邮箱地址（如 `xxx@gmail.com` 或 `xxx@qq.com`） |
| `MAIL_PASSWORD` | 邮箱授权码（非登录密码） |

**可选：**

| Secret | 默认值 | 说明 |
|--------|--------|------|
| `MAIL_TO` | 同 MAIL_USER | 收件邮箱 |
| `SMTP_HOST` | smtp.gmail.com | Gmail 用默认值，QQ 邮箱填 `smtp.qq.com` |
| `SMTP_PORT` | 465 | 一般不用改 |
| `GITHUB_TOKEN` | 无 | 提高 GitHub API 限额（60→5000 次/小时） |

### 3. 启用 Actions

Actions → "GitHub Trending Daily" → Enable workflow

点击 "Run workflow" 手动测试一次，收到邮件即成功。

## QQ 邮箱示例

Secrets 配置：

```
GEMINI_API_KEY  =  AIzaSy...
MAIL_USER       =  123456@qq.com
MAIL_PASSWORD   =  xxxxxxxxxxxxxxxx（授权码，不是 QQ 密码）
SMTP_HOST       =  smtp.qq.com
```

## 本地测试

```bash
pip install -r requirements.txt

# Gmail
set MAIL_USER=xxx@gmail.com
set MAIL_PASSWORD=xxxx
python main.py

# QQ 邮箱
set MAIL_USER=xxx@qq.com
set MAIL_PASSWORD=授权码
set SMTP_HOST=smtp.qq.com
python main.py
```

## 费用

| 项目 | 费用 |
|------|------|
| Gemini API (每天 1 次) | 免费 (1500次/天额度) |
| GitHub Actions | 免费 |
| 邮箱 SMTP | 免费 |
| **总计** | **$0** |

# GitHub Trending 日报

每天早 8 点自动推送 GitHub Trending Top 10 到邮箱，AI 深度分析。

**永久免费**：GitHub Actions (免费) + Agnes AI (免费) + 邮箱 SMTP (免费)

## 部署 (3 步)

### 1. 获取密钥

| 密钥 | 获取方式 |
|------|---------|
| Agnes AI Key | `sk-` 开头，如果已有 see.py 的 vision key 可以共用 |
| 邮箱授权码 | **QQ 邮箱**: 设置 → 账户 → POP3/SMTP 服务 → 开启 → 生成授权码 |
|  | **Gmail**: 账号 → 安全 → 两步验证 → App Password |

### 2. Fork 并配置 Secrets

在 Settings → Secrets and variables → Actions 添加：

**必填：**

| Secret | 说明 |
|--------|------|
| `LLM_API_KEY` | Agnes AI Key (`sk-` 开头) |
| `MAIL_USER` | 邮箱地址 |
| `MAIL_PASSWORD` | 邮箱授权码 |

**可选（QQ 邮箱必填）：**

| Secret | 说明 |
|--------|------|
| `SMTP_HOST` | QQ 邮箱填 `smtp.qq.com`，Gmail 不用填 |

### 3. 启用 Actions

Actions → "GitHub Trending Daily" → Enable workflow → Run workflow 测试

## 费用

| 项目 | 费用 |
|------|------|
| Agnes AI | 免费 |
| GitHub Actions | 免费 |
| 邮箱 SMTP | 免费 |
| **总计** | **$0** |

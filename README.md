# MT-AutoCheckIn

一个基于 Python 的 M-Team 自动签到工具，用于解决"连续40天不登录将被删除账号"的问题。通过自动化的方式，确保您的账号始终保持活跃状态。

## 📝 项目介绍

本项目使用 Python 编写，通过模拟真实浏览器行为实现自动登录和签到功能。主要解决以下问题：
- 防止账号因长期不登录被删除
- 自动完成每日签到
- 支持多种通知方式，实时掌握签到状态

## ✨ 特性

- 🌟 使用 Playwright 模拟真实浏览器行为，更稳定可靠
- 🔄 支持 LocalStorage 持久化，减少不必要的登录操作
- ⏰ 内置定时任务调度器，支持自定义执行时间
- 🎲 执行时间随机化，模拟真实用户行为
- 📧 支持多种通知方式：
  - SMTP 邮件通知
  - Telegram 消息通知
  - 飞书通知

## 🔧 环境要求

- Python 3.8 或更高版本
- 稳定的网络连接
- Docker（如果使用 Docker 部署）

## 📋 准备工作

在开始使用之前，请准备以下信息：

1. **M-Team 账号信息**：
   - 用户名
   - 密码
   - TOTP Secret（从二级验证的二维码中获取）

2. **通知配置**（可选）：
   - SMTP：邮箱服务器信息
   - Telegram：Bot Token 和 Chat ID
   - 飞书：Webhook 地址

## 🚀 使用方法

### 方式一：直接运行

```bash
# 克隆项目
git clone https://github.com/0xBitwild/MT-AutoCheckIn.git

# 进入项目目录
cd MT-AutoCheckIn

# 配置虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装配置 Playwright
playwright install
playwright install-deps

# 配置环境变量
cp .env.example .env
vi .env  # 编辑配置文件

# 运行程序
python3 MT-AutoCheckIn.py
```

### 方式二：Docker Compose 部署

```bash
# 克隆项目
git clone https://github.com/0xBitwild/MT-AutoCheckIn.git

# 进入项目目录
cd MT-AutoCheckIn

# 配置环境变量
cp .env.example .env
vi .env  # 编辑配置文件

# 启动服务
docker compose up -d
```

## ⚙️ 配置说明

在 `.env` 文件中配置以下环境变量：

```ini
# 必需配置
MT_USERNAME=你的用户名
MT_PASSWORD=你的密码
MT_TOTP_SECRET=你的TOTP密钥

# 可选配置 - 邮件通知
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-password
SMTP_TO=receiver@example.com

# 可选配置 - Telegram通知
TG_BOT_TOKEN=your-bot-token
TG_CHAT_ID=your-chat-id

# 可选配置 - 飞书通知
FEISHU_WEBHOOK=your-webhook-url
```

## 📅 定时任务

默认情况下，程序会每天随机选择一个时间执行签到任务。您可以通过修改代码中的调度器配置来自定义执行时间。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来帮助改进这个项目！

## 📜 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## ⚠️ 免责声明

本项目仅供学习和研究使用，请遵守相关网站的使用规则和条款。对于因使用本项目而导致的任何问题，作者不承担任何责任。

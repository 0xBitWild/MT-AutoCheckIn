# MT-AutoCheckIn

一个M-Team自动登录签到脚本，解决“连续40天不登录将被删除账号”的问题。

## 特点

- 使用Playwright模拟浏览器登录；
- 支持LocalStorage保存及复用；
- 使用Schedule执行定时任务；
- 默认每天执行一次任务，执行时间做了随机化处理；
- 支持SMTP/Telegram通知；

## 准备工作

- **用户名**：M-Team帐号；
- **密码**：M-Team帐号密码；
- **TOTP Secret**：从启用“动态验证码二级验证”的二维码中提取；

## 使用方法

### 直接运行

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

# 安装配置Playwright
playwright install
playwright install-deps

# 配置环境变量
vi .env

# 运行
python3 MT-AutoCheckIn.py

```

### Docker Compose 部署

```bash

# 克隆项目
git clone https://github.com/0xBitwild/MT-AutoCheckIn.git

# 进入项目目录
cd MT-AutoCheckIn

# 修改docker-compose.yml中的环境变量配置
vi docker-compose.yml

# 启动
docker compose up -d

```

"""MTeam自动签到脚本。"""

import os
import json
import time
import random
import logging
import smtplib
import asyncio
from typing import Any
from email.mime.text import MIMEText
from pathlib import Path

import pyotp
import requests
import schedule
import humanize
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page
from playwright.async_api import (TimeoutError as PlaywrightTimeoutError,
                                  Error as PlaywrightError)

# 配置日是记录器
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s - %(lineno)d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    # filename=Path(__file__).stem + '.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

load_dotenv()


class LocalStorageLoginError(Exception):
    """LocalStorage登录失败异常。"""


class PasswordLoginError(Exception):
    """密码登录失败异常。"""


class Notifier:
    """通知发送类，支持多种通知方式。"""

    def __init__(self):
        self.smtp_config = None
        self.telegram_config = None

        self._configure()

    def _configure(self):
        """配置通知方式。"""

        notify_type = os.environ.get('NOTIFY_TYPE')

        if notify_type == 'smtp':
            self._configure_smtp()
        elif notify_type == 'telegram':
            self._configure_telegram()
        else:
            logger.warning("未设置通知类型，将不发送通知")

    def _configure_smtp(self):
        """配置SMTP服务器信息。"""

        if not all([os.environ.get('SMTP_HOST'),
                    os.environ.get('SMTP_PORT'),
                    os.environ.get('SMTP_USERNAME'),
                    os.environ.get('SMTP_PASSWORD')]
                   ):
            raise ValueError(
                "请设置所有必要的环境变量：SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD"
                )

        self.smtp_config = {
            'host': os.environ.get('SMTP_HOST'),
            'port': os.environ.get('SMTP_PORT'),
            'username': os.environ.get('SMTP_USERNAME'),
            'password': os.environ.get('SMTP_PASSWORD')
        }

    def _configure_telegram(self):
        """配置Telegram机器人信息。"""

        if not all(
            [os.environ.get('TELEGRAM_BOT_TOKEN'),
             os.environ.get('TELEGRAM_CHAT_ID')]):
            raise ValueError(
                "请设置所有必要的环境变量：TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID"
                )

        self.telegram_config = {
            'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN'),
            'chat_id': os.environ.get('TELEGRAM_CHAT_ID')
        }

    def send_smtp(self, subject, message, to_email):
        """通过SMTP发送邮件通知。"""
        if not self.smtp_config:
            raise ValueError("SMTP配置未设置")

        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = f'MT-AutoCheckIn <{self.smtp_config["username"]}>'
        msg['To'] = to_email

        try:
            with smtplib.SMTP_SSL(
                self.smtp_config['host'],
                int(self.smtp_config['port']),
                timeout=30
            ) as server:
                server.login(
                    self.smtp_config['username'],
                    self.smtp_config['password']
                    )
                # logger.info("SMTP登录成功")
                server.send_message(msg)
                logger.info("SMTP邮件发送成功")
                server.quit()
        except smtplib.SMTPException as e:
            logger.error("发送邮件时发生未知错误: %s", str(e))

    def send_telegram(self, message):
        """通过Telegram发送通知。"""
        if not self.telegram_config:
            raise ValueError("Telegram配置未设置")

        url = f"https://api.telegram.org/bot{self.telegram_config['bot_token']}/sendMessage"
        payload = {
            'chat_id': self.telegram_config['chat_id'],
            'text': message
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Telegram消息发送成功")
        except requests.RequestException as e:
            logger.error("Telegram消息发送失败: %s", str(e))

    def send_notification(self, message, subject=None):
        """发送通知，根据配置选择发送方式。"""
        to_email = os.environ.get('NOTIFY_EMAIL')
        if self.smtp_config and to_email:
            self.send_smtp(subject or "通知", message, to_email)
        if self.telegram_config:
            self.send_telegram(message)


class LocalStorageManager:
    """Local Storage管理类。"""

    def __init__(self, page: Page) -> None:
        self.page = page

    async def get_value(self, key: str) -> str:
        """获取Local Storage中的值。"""
        return await self.page.evaluate(f'localStorage.getItem("{key}")')

    async def set_value(self, key: str, value: str) -> None:
        """设置Local Storage中的值。"""
        escaped_value = json.dumps(value)
        await self.page.evaluate(
            f'localStorage.setItem("{key}", {escaped_value})'
            )

    async def remove_value(self, key: str) -> None:
        """删除Local Storage中的指定键值对。"""
        await self.page.evaluate(f'localStorage.removeItem("{key}")')

    async def clear(self) -> None:
        """清空Local Storage中的所有数据。"""
        await self.page.evaluate('localStorage.clear()')

    async def save_to_file(self, filename: str) -> None:
        """将Local Storage保存到本地json文件。"""
        storage_data = await self.page.evaluate(
            '() => JSON.stringify(localStorage)'
            )
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(
                json.loads(storage_data),
                f,
                ensure_ascii=False,
                indent=4
                )

    async def load_from_file(self, filename: str) -> None:
        """从本地json文件加载数据到Local Storage。"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                storage_data = json.load(f)
            for key, value in storage_data.items():
                try:
                    await self.set_value(key, value)
                except (PlaywrightError, ValueError) as e:
                    logger.error("设置键 '%s' 的值时出错: %s", key, str(e))
        except FileNotFoundError:
            logger.warning("文件 %s 不存在，无法加载Local Storage数据。", filename)
        except json.JSONDecodeError:
            logger.error("文件 %s 不是有效的JSON格式，无法加载Local Storage数据。", filename)
        except IOError as e:
            logger.error("读取文件 %s 时发生I/O错误: %s", filename, str(e))
        except Exception as e:
            logger.error("加载Local Storage数据时发生未预期的错误: %s", str(e))
            raise


class MTeamSpider:
    """M-Team 自动签到爬虫类。"""

    def __init__(self) -> None:

        self.localstorage_file: Path = Path(__file__).parent / 'mteam_localstorage.json'
        self.username: str = os.environ.get('MTEAM_USERNAME', '')
        self.password: str = os.environ.get('MTEAM_PASSWORD', '')
        self.totp_secret: str = os.environ.get('MTEAM_TOTP_SECRET', '')

        self.profile_api_endpoint: str = '/api/member/profile'
        self.profile_json: dict[str, Any] = {}

        self.notify_subject_prefix: str = '[MT-AutoCheckIn] '

        if not all([self.username,
                    self.password,
                    self.totp_secret]):
            raise ValueError(
                "请设置所有必要的环境变量：MTEAM_USERNAME, MTEAM_PASSWORD, MTEAM_TOTP_SECRET"
                )

        self.notifier: Notifier = Notifier()

    def _get_captcha_code(self) -> str:

        totp = pyotp.TOTP(self.totp_secret)
        captcha_code = totp.now()

        return captcha_code

    def _parse_profile_json(self) -> str:
        """解析API响应数据。"""

        data: dict[str, Any] | None = self.profile_json.get('data')

        if not data:
            return '获取到的数据为空'

        message = f'用户ID: {data.get("id")}\n'
        message += f'用户名: {data.get("username")}\n'
        message += f'用户Email: {data.get("email")}\n'
        message += f'登录IP: {data.get("ip")}\n'
        message += f'账户创建时间: {data.get("createdDate")}\n'
        message += f'账户更新时间: {data.get("lastModifiedDate")}\n'

        member_status: dict[str, Any] | None = data.get('memberStatus')
        if not member_status:
            message += '会员状态数据为空\n'
        else:
            message += f'会员创建时间: {member_status.get("createdDate")}\n'
            message += f'会员更新时间: {member_status.get("lastModifiedDate")}\n'
            message += f'会员最新登录时间: {member_status.get("lastLogin")}\n'
            message += f'会员最新浏览时间: {member_status.get("lastBrowse")}\n'

        member_count: dict[str, Any] | None = data.get('memberCount')
        if not member_count:
            message += '会员统计数据为空\n'
        else:
            uploaded = humanize.naturalsize(member_count.get('uploaded', 0), binary=True)
            downloaded = humanize.naturalsize(member_count.get('downloaded', 0), binary=True)

            message += f'上传量: {uploaded}\n'
            message += f'下载量: {downloaded}\n'
            message += f'魔力值: {member_count.get("bonus")}\n'
            message += f'分享率: {member_count.get("shareRate")}\n'

        return message

    async def intercept_profile_request(self, route, request):
        """拦截请求并处理API响应。"""

        logger.info("拦截到请求: %s", request.url)

        if request.url.endswith(self.profile_api_endpoint):
            logger.info("成功匹配到目标请求: %s", request.url)
            try:
                response = await route.fetch()
                json_data = await response.json()
                self.profile_json = json_data
                # logger.info("获取到的响应数据: %s", self.profile_json)
                await route.continue_()
            except (json.JSONDecodeError, PlaywrightError) as e:
                logger.warning("获取API数据时出错: %s", e)
        else:
            await route.continue_()

    async def login_by_localstorage(self,
                                    page: Page,
                                    local_storage_manager: LocalStorageManager
                                    ) -> None:
        """使用保存的 LocalStorage 数据尝试登录 M-Team。"""

        logger.info('开始通过LocalStorage登录')

        try:
            # 加载LocalStorage
            await local_storage_manager.load_from_file(str(self.localstorage_file))

            # 刷新页面
            await page.reload(timeout=60000)

            # 等待页面加载完成
            await page.wait_for_load_state('networkidle', timeout=60000)
            await page.wait_for_timeout(timeout=60000)

            # 登录状态检查
            is_logged_in = (
                page.url == 'https://kp.m-team.cc/index' and
                self.profile_json and
                self.profile_json.get('data') and
                self.profile_json.get('data').get('username') == self.username  # type: ignore
            )

            if is_logged_in:

                logger.info('通过LocalStorage登录成功')
                self.notifier.send_notification(
                    message=f'通过LocalStorage登录成功\n\n{self._parse_profile_json()}',
                    subject=f'{self.notify_subject_prefix}登录成功'
                    )

                # 保存localstorage到文件
                await local_storage_manager.save_to_file(str(self.localstorage_file))
                logger.info('已保存更新LocalStorage到文件')
                return

            logger.warning('通过LocalStorage登录失败')
            raise LocalStorageLoginError('通过LocalStorage登录失败')

        except PlaywrightError as e:
            logger.error('通过LocalStorage登录时发生错误: %s', str(e))

    async def login_by_password(self,
                                page: Page,
                                local_storage_manager: LocalStorageManager
                                ) -> None:
        """使用用户名和密码登录 M-Team。"""

        logger.info('开始通过用户名密码登录')

        try:

            if page.url != 'https://kp.m-team.cc/login':
                # 访问登录页
                await page.goto('https://kp.m-team.cc/login', timeout=60000)  # 60秒超时

            # 等待页面加载完成
            await page.wait_for_load_state('networkidle', timeout=60000)  # 60秒超时

            # 输入用户名/密码
            await page.locator('button[type="submit"]').wait_for(timeout=60000)
            await page.locator('input[id="username"]').fill(self.username)
            await page.locator('input[id="password"]').fill(self.password)
            await page.locator('button[type="submit"]').click()

            try:
                # 等待2FA页面加载完成
                await page.locator('input[id="otpCode"]').wait_for(timeout=60000)

                # 获取并输入2FA验证码
                captcha_code = self._get_captcha_code()
                await page.locator('input[id="otpCode"]').fill(captcha_code)
                await page.locator('button[type="submit"]').click()

                # 等待页面加载完成
                await page.wait_for_load_state('networkidle', timeout=60000)  # 60秒超时
                await page.wait_for_timeout(timeout=60000)

            except PlaywrightTimeoutError as e:
                logger.warning('处理2FA时发生超时错误: %s', str(e))
            except PlaywrightError as e:
                logger.warning('处理2FA时发生Playwright错误: %s', str(e))

            # 登录状态检查
            is_logged_in = (
                page.url == 'https://kp.m-team.cc/index' and
                self.profile_json and
                self.profile_json.get('data') and
                self.profile_json.get('data').get('username') == self.username  # type: ignore
            )

            if is_logged_in:

                logger.info('通过用户名密码登录成功')
                self.notifier.send_notification(
                    message=f'通过用户名密码登录成功\n\n{self._parse_profile_json()}',
                    subject=f'{self.notify_subject_prefix}登录成功'
                    )

                # 保存localstorage到文件
                await local_storage_manager.save_to_file(str(self.localstorage_file))
                logger.info('已保存LocalStorage到文件')
                return

            logger.warning('通过用户名密码登录失败')
            raise PasswordLoginError('通过用户名密码登录失败')

        except PlaywrightError as e:
            logger.error('通过用户名密码登录时发生错误: %s', str(e))
            raise PlaywrightError(f'通过用户名密码登录时发生错误: {str(e)}') from e

    async def check_in(self):
        """执行M-Team自动签到流程。"""
        logger.info("开始执行签到流程")

        # 随机等待10到300秒
        random_delay = random.randint(10, 300)
        logger.info("等待 %s 秒后开始签到", random_delay)
        time.sleep(random_delay)

        async with async_playwright() as playwright:

            # 启动浏览器
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()

            # 设置请求拦截
            await page.route(f"**{self.profile_api_endpoint}", self.intercept_profile_request)
            logger.info("请求拦截设置完成")

            # 访问主页
            await page.goto('https://kp.m-team.cc/', timeout=60000)
            await page.wait_for_load_state('networkidle', timeout=60000)

            # 初始化LocalStorage管理器
            local_storage_manager = LocalStorageManager(page)

            try:
                try:
                    # 尝试通过LocalStorage登录
                    await self.login_by_localstorage(page, local_storage_manager)
                except LocalStorageLoginError:
                    # 尝试通过用户名密码登录
                    logger.warning('通过LocalStorage登录失败，尝试通过用户名密码登录')
                    try:
                        await self.login_by_password(page, local_storage_manager)
                    except PasswordLoginError:
                        logger.error('通过用户名密码登录失败，即将发送通知')
                        self.notifier.send_notification(
                            message='通过用户名密码登录失败',
                            subject=f'{self.notify_subject_prefix}登录失败'
                        )
                        raise  # 可选：向上传递异常
            except PlaywrightError as e:
                logger.error('签到时发生Playwright错误: %s', str(e))
                self.notifier.send_notification(
                    message=f'签到时发生Playwright错误: {str(e)}',
                    subject=f'{self.notify_subject_prefix}登录失败'
                )
            except KeyboardInterrupt:
                logger.info('用户终止运行')
            finally:
                await page.unroute(f"**{self.profile_api_endpoint}")
                await page.close()
                await browser.close()

    def schedule_check_in(self):
        """定时签到。"""

        logger.info('定时签到任务开始...')

        self.notifier.send_notification(
            message='定时签到任务开始',
            subject="[MT-AutoCheckIn] 定时签到任务开始"
        )

        # 生成9:00到12:00之间的随机时间
        random_hour = random.randint(9, 11)
        random_minute = random.randint(0, 59)
        random_time = f"{random_hour:02d}:{random_minute:02d}"

        # 包装异步调用
        def run_check_in():
            asyncio.run(self.check_in())

        # 每天在生成的随机时间签到
        schedule.every().day.at(random_time).do(run_check_in)

        logger.info("已设置每天 %s 进行签到", random_time)

        # 每小时执行一次心跳
        def heartbeat():
            logger.info('定时签到任务正在运行...')

        schedule.every().hour.do(heartbeat)

        while True:
            schedule.run_pending()
            time.sleep(60)


if __name__ == '__main__':

    # asyncio.run(MTeamSpider().check_in())
    MTeamSpider().schedule_check_in()

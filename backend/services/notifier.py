from typing import Optional, Dict
from typing import Optional, Dict
# backend/services/notifier.py
import aiohttp
from typing import Optional
from config import config
from utils.logger import get_logger

logger = get_logger("notifier")


class Notifier:
    """通知服务 - Telegram & Discord"""

    def __init__(self):
        self.telegram_token = config.TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = config.TELEGRAM_CHAT_ID
        self.discord_webhook = config.DISCORD_WEBHOOK_URL
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def send_trade_alert(self, trade: dict):
        """发送交易提醒"""
        emoji = "🟢" if trade.get('profit_loss', 0) >= 0 else "🔴"
        message = (
            f"{emoji} **交易信号**\n"
            f"Agent: {trade['agent_name']}\n"
            f"市场: {trade.get('market_title', trade['market_id'])}\n"
            f"方向: {trade['direction']}\n"
            f"价格: ${trade['entry_price']:.4f}\n"
            f"仓位: ${trade['size']:.2f}\n"
            f"边际: {trade.get('edge', 0):.2%}\n"
            f"原因: {trade.get('reasoning', 'N/A')}"
        )
        await self._send_telegram(message)
        await self._send_discord(message)

    async def send_daily_report(self, stats: dict):
        """发送每日报告"""
        message = (
            f"📊 **每日报告**\n"
            f"总交易: {stats.get('total_trades', 0)}\n"
            f"胜率: {stats.get('win_rate', 0):.1f}%\n"
            f"总盈亏: ${stats.get('total_pnl', 0):.2f}\n"
            f"今日盈亏: ${stats.get('daily_pnl', 0):.2f}"
        )
        await self._send_telegram(message)
        await self._send_discord(message)

    async def send_alert(self, message: str):
        """发送一般提醒"""
        await self._send_telegram(f"⚠️ {message}")
        await self._send_discord(f"⚠️ {message}")

    async def _send_telegram(self, message: str):
        if not self.telegram_token or not self.telegram_chat_id:
            return

        session = await self._get_session()
        try:
            await session.post(
                f"https://api.telegram.org/bot{self.telegram_token}/sendMessage",
                json={
                    "chat_id": self.telegram_chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }
            )
        except Exception as e:
            logger.error(f"Telegram通知失败: {e}")

    async def _send_discord(self, message: str):
        if not self.discord_webhook:
            return

        session = await self._get_session()
        try:
            await session.post(
                self.discord_webhook,
                json={"content": message}
            )
        except Exception as e:
            logger.error(f"Discord通知失败: {e}")

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


notifier = Notifier()
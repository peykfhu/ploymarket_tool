
import time

import math

from typing import Dict, Tuple

from config import config

from database import db

from utils.logger import get_logger



logger = get_logger("risk_manager")





class RiskManager:

    """

    大神级风控 v4



    模拟盘：使用 initial_balance 设置 + 累计PnL

    实盘：获取 Polymarket 真实账户余额

    """



    def __init__(self):

        self._consecutive_losses = 0

        self._pause_until = 0.0

        self.reload_settings()



    def reload_settings(self):

        self.max_position_size = db.get_setting('max_position_size', config.MAX_POSITION_SIZE)

        self.max_daily_loss = db.get_setting('max_daily_loss', config.MAX_DAILY_LOSS)

        self.min_edge = db.get_setting('min_edge', config.MIN_EDGE_THRESHOLD)

        self.max_concurrent = db.get_setting('max_concurrent', config.MAX_CONCURRENT_POSITIONS)

        self.stop_loss_pct = db.get_setting('stop_loss', config.STOP_LOSS_PERCENT)

        self.daily_drawdown_limit = db.get_setting('daily_drawdown_limit', config.DAILY_DRAWDOWN_LIMIT)

        self.initial_balance = db.get_setting('initial_balance', config.INITIAL_BALANCE)



    async def get_balance(self) -> float:

        """模拟盘用设置余额，实盘获取真实余额"""

        if config.DRY_RUN:

            stats = db.get_all_stats()

            return self.initial_balance + (stats.get('total_pnl', 0) or 0)

        else:

            from services.polymarket_client import polymarket_client

            real = await polymarket_client.get_balance()

            if real is not None:

                return real

            # 获取失败 fallback

            stats = db.get_all_stats()

            return self.initial_balance + (stats.get('total_pnl', 0) or 0)



    def get_balance_sync(self) -> float:

        """同步版（用于非async场景）"""

        stats = db.get_all_stats()

        return self.initial_balance + (stats.get('total_pnl', 0) or 0)



    def can_trade(self, signal) -> Tuple[bool, str]:

        self.reload_settings()



        # 连败暂停

        if time.time() < self._pause_until:

            remaining = int(self._pause_until - time.time())

            return False, f"连败暂停 {remaining}s"



        # 日回撤 15% 硬止损

        balance = self.get_balance_sync()

        today_pnl = db.get_today_pnl()

        if balance > 0 and today_pnl < 0:

            drawdown = abs(today_pnl) / balance

            if drawdown >= self.daily_drawdown_limit:

                return False, f"⛔ 日回撤{drawdown:.1%}超限，全天停止"



        daily_loss = db.get_daily_loss()

        if daily_loss >= self.max_daily_loss:

            return False, f"日亏损上限 ${daily_loss:.2f}"



        if signal.edge < self.min_edge:

            return False, f"边际不足 {signal.edge:.2%}"



        open_pos = db.get_open_positions()

        if len(open_pos) >= self.max_concurrent:

            return False, f"持仓满 {len(open_pos)}/{self.max_concurrent}"



        for pos in open_pos:

            if pos['market_id'] == signal.market_id:

                return False, "已有持仓"



        if signal.confidence < 0.4:

            return False, f"置信度不足 {signal.confidence:.2%}"



        return True, "✅ 通过"



    def calculate_position_size(self, edge: float, confidence: float,

                                 strategy: str = "info_arb") -> float:

        balance = self.get_balance_sync()

        if edge <= 0 or confidence <= 0 or balance <= 0:

            return 0



        if strategy == "endgame":

            # 尾盘：固定 3-5% 仓位

            size = balance * 0.03

            if edge < 0.05 and confidence > 0.95:

                size = balance * 0.05

            return round(min(size, self.max_position_size), 2)



        # 信息差：1/4 Kelly

        b = max(1 / edge, 1)

        p = confidence

        q = 1 - p

        kelly = max((b * p - q) / b, 0)

        quarter_kelly = kelly / 4



        loss_mult = max(0.2, 1 - self._consecutive_losses * 0.2)

        size = balance * quarter_kelly * loss_mult

        size = min(size, self.max_position_size, balance * 0.08)



        return round(max(size, 0), 2)



    def should_exit(self, trade: Dict, current_price: float) -> Tuple[bool, str]:

        entry = trade['entry_price']

        strategy = trade.get('strategy', 'info_arb')

        if entry <= 0:

            return False, ""



        if trade['direction'] in ('BUY_YES', 'BUY_NO'):

            pnl_pct = (current_price - entry) / entry

        else:

            pnl_pct = (entry - current_price) / entry



        # 硬止损

        if pnl_pct <= -self.stop_loss_pct:

            self.record_loss()

            return True, f"止损 {pnl_pct:.2%}"



        # 信息差：30分钟不涨就跑

        if strategy == 'info_arb':

            from datetime import datetime

            created = trade.get('created_at', '')

            if created:

                try:

                    ct = datetime.fromisoformat(str(created).replace('Z', '+00:00')).replace(tzinfo=None)

                    elapsed = (datetime.utcnow() - ct).total_seconds()

                    if elapsed > 1800 and pnl_pct < 0.02:

                        return True, f"超时(30min) {pnl_pct:.2%}"

                except:

                    pass



        # 尾盘：等到99¢+

        if strategy == 'endgame':

            if current_price >= 0.995:

                self.record_win()

                return True, f"尾盘止盈 {current_price:.4f}"

            if pnl_pct <= -0.05:

                self.record_loss()

                return True, f"尾盘反转止损 {pnl_pct:.2%}"

            return False, ""



        # 确定性止盈

        if current_price >= 0.92:

            self.record_win()

            return True, f"止盈 {current_price:.4f}"



        # 边际修复

        if trade.get('edge') and pnl_pct > 0 and pnl_pct >= trade['edge'] * 0.6:

            self.record_win()

            return True, f"边际修复 +{pnl_pct:.2%}"



        return False, ""



    def record_win(self):

        self._consecutive_losses = 0



    def record_loss(self):

        self._consecutive_losses += 1

        if self._consecutive_losses >= 5:

            self._pause_until = time.time() + 1800

            db.add_activity("风控", "连败暂停",

                            f"连亏{self._consecutive_losses}次，暂停30min", "🛑")





risk_manager = RiskManager()


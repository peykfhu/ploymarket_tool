# backend/services/risk_manager.py
from typing import Dict, Optional
from config import config
from database import db
from utils.logger import get_logger

logger = get_logger("risk_manager")


class RiskManager:
    """风险管理器"""

    def __init__(self):
        self.max_position_size = config.MAX_POSITION_SIZE
        self.max_daily_loss = config.MAX_DAILY_LOSS
        self.min_edge = config.MIN_EDGE_THRESHOLD
        self.max_concurrent = config.MAX_CONCURRENT_POSITIONS
        self.stop_loss_pct = config.STOP_LOSS_PERCENT

    def can_trade(self, signal) -> tuple[bool, str]:
        """检查是否允许交易"""
        # 1. 检查最小边际
        if signal.edge < self.min_edge:
            return False, f"边际不足: {signal.edge:.2%} < {self.min_edge:.2%}"

        # 2. 检查仓位数量
        open_positions = db.get_open_positions()
        if len(open_positions) >= self.max_concurrent:
            return False, f"持仓已满: {len(open_positions)}/{self.max_concurrent}"

        # 3. 检查每日亏损
        daily_loss = db.get_daily_loss()
        if daily_loss >= self.max_daily_loss:
            return False, f"已达每日亏损上限: ${daily_loss:.2f} >= ${self.max_daily_loss}"

        # 4. 检查单笔仓位大小
        if signal.size > self.max_position_size:
            return False, f"仓位过大: ${signal.size} > ${self.max_position_size}"

        # 5. 检查重复市场
        for pos in open_positions:
            if pos['market_id'] == signal.market_id:
                return False, f"该市场已有持仓: {signal.market_id}"

        # 6. 检查置信度
        if signal.confidence < 0.5:
            return False, f"置信度不足: {signal.confidence:.2%}"

        return True, "通过风控检查"

    def calculate_position_size(self, edge: float, confidence: float,
                                 balance: float) -> float:
        """使用改良凯利公式计算仓位大小"""
        # Kelly Criterion: f* = (bp - q) / b
        # 这里使用半凯利（Half Kelly）更保守
        b = 1 / edge if edge > 0 else 1  # 赔率
        p = confidence  # 胜率
        q = 1 - p  # 败率

        kelly = (b * p - q) / b
        half_kelly = kelly / 2

        # 限制最大仓位
        size = min(
            balance * max(half_kelly, 0),
            self.max_position_size,
            balance * 0.1  # 最多10%资金
        )

        return round(max(size, 0), 2)

    def should_exit(self, trade: Dict, current_price: float) -> tuple[bool, str]:
        """检查是否应该平仓"""
        entry_price = trade['entry_price']

        # 止损检查
        if trade['direction'] in ('BUY_YES', 'BUY_NO'):
            loss_pct = (entry_price - current_price) / entry_price
            if loss_pct >= self.stop_loss_pct:
                return True, f"触发止损: {loss_pct:.2%}"

        # 止盈：价格接近1（市场确认）
        if current_price >= 0.90:
            return True, f"止盈: 价格已达 {current_price:.2f}"

        # 价格修复：边际消失
        if trade.get('edge'):
            original_edge = trade['edge']
            current_edge = abs(current_price - entry_price) / entry_price
            if current_edge < original_edge * 0.2:
                return True, "边际已修复"

        return False, ""


risk_manager = RiskManager()
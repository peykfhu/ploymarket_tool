# backend/agents/base_agent.py
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime
from models import Signal, AgentState, AgentStatus
from services.polymarket_client import polymarket_client
from services.risk_manager import risk_manager
from services.notifier import notifier
from database import db
from utils.logger import get_logger


class BaseAgent(ABC):
    """所有套利代理的基类"""

    def __init__(self, name: str, interval_seconds: int = 600):
        self.name = name
        self.interval = interval_seconds
        self.logger = get_logger(f"agent.{name}")
        self.state = AgentState(name=name)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.polymarket = polymarket_client

    @abstractmethod
    async def scan_opportunities(self) -> List[Signal]:
        """扫描套利机会 - 子类必须实现"""
        pass

    async def start(self):
        """启动代理"""
        if self._running:
            self.logger.warning(f"{self.name} 已在运行")
            return

        self._running = True
        self.state.status = AgentStatus.RUNNING
        self.logger.info(f"🚀 {self.name} 启动")
        db.log_agent(self.name, "INFO", "Agent启动")

        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """停止代理"""
        self._running = False
        self.state.status = AgentStatus.STOPPED
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.logger.info(f"⏹ {self.name} 已停止")
        db.log_agent(self.name, "INFO", "Agent停止")

    async def _run_loop(self):
        """主循环"""
        while self._running:
            try:
                self.state.last_activity = datetime.utcnow()

                # 扫描机会
                signals = await self.scan_opportunities()

                for signal in signals:
                    await self._process_signal(signal)

                # 检查现有持仓是否需要平仓
                await self._check_exits()

            except Exception as e:
                self.state.errors += 1
                self.logger.error(f"运行异常: {e}", exc_info=True)
                db.log_agent(self.name, "ERROR", f"运行异常: {str(e)}")

                if self.state.errors > 10:
                    self.state.status = AgentStatus.ERROR
                    await notifier.send_alert(
                        f"⛔ {self.name} 错误过多({self.state.errors}次)，已暂停"
                    )
                    self._running = False
                    break

            await asyncio.sleep(self.interval)

    async def _process_signal(self, signal: Signal):
        """处理交易信号"""
        # 风控检查
        can_trade, reason = risk_manager.can_trade(signal)
        if not can_trade:
            self.logger.info(f"风控拦截: {reason}")
            db.log_agent(self.name, "WARNING", f"风控拦截: {reason}")
            return

        # 计算仓位
        stats = db.get_all_stats()
        balance = 150 + (stats.get('total_pnl', 0) or 0)  # 初始资金 + 累计盈亏
        position_size = risk_manager.calculate_position_size(
            signal.edge, signal.confidence, balance
        )

        if position_size < 1:
            self.logger.info(f"仓位太小，跳过: ${position_size}")
            return

        signal.size = position_size

        # 下单
        order = await self.polymarket.place_order(
            token_id=signal.market_id,
            side="BUY" if "BUY" in signal.direction else "SELL",
            price=signal.entry_price,
            size=signal.size
        )

        if order:
            # 记录交易
            trade_id = db.record_trade({
                'agent_name': self.name,
                'market_id': signal.market_id,
                'market_title': signal.market_title,
                'direction': signal.direction,
                'entry_price': signal.entry_price,
                'size': signal.size,
                'edge': signal.edge,
                'confidence': signal.confidence,
                'reasoning': signal.reasoning,
                'metadata': signal.metadata,
            })

            self.state.total_trades += 1
            self.state.last_signal = signal.reasoning

            self.logger.info(
                f"✅ 下单成功 #{trade_id}: {signal.direction} "
                f"${signal.size:.2f}@{signal.entry_price:.4f} "
                f"边际={signal.edge:.2%}"
            )

            # 发通知
            await notifier.send_trade_alert({
                'agent_name': self.name,
                'market_id': signal.market_id,
                'market_title': signal.market_title,
                'direction': signal.direction,
                'entry_price': signal.entry_price,
                'size': signal.size,
                'edge': signal.edge,
                'reasoning': signal.reasoning,
            })

            db.log_agent(self.name, "INFO", f"下单成功 #{trade_id}", {
                'signal': signal.__dict__ if hasattr(signal, '__dict__') else str(signal)
            })

    async def _check_exits(self):
        """检查是否需要平仓"""
        open_positions = db.get_open_positions()

        for pos in open_positions:
            if pos['agent_name'] != self.name:
                continue

            try:
                current_price = await self.polymarket.get_price(pos['market_id'])
                if current_price is None:
                    continue

                should_exit, reason = risk_manager.should_exit(pos, current_price)

                if should_exit:
                    # 计算盈亏
                    if pos['direction'] in ('BUY_YES', 'BUY_NO'):
                        pnl = (current_price - pos['entry_price']) * pos['size']
                    else:
                        pnl = (pos['entry_price'] - current_price) * pos['size']

                    # 平仓
                    await self.polymarket.place_order(
                        token_id=pos['market_id'],
                        side="SELL" if "BUY" in pos['direction'] else "BUY",
                        price=current_price,
                        size=pos['size']
                    )

                    db.close_trade(pos['id'], current_price, pnl)

                    emoji = "💰" if pnl > 0 else "💸"
                    self.logger.info(
                        f"{emoji} 平仓 #{pos['id']}: {reason}, PnL=${pnl:.2f}"
                    )

            except Exception as e:
                self.logger.error(f"检查平仓异常: {e}")

    def get_state(self) -> Dict:
        """获取代理状态"""
        stats = db.get_agent_stats(self.name)
        return {
            "name": self.name,
            "status": self.state.status.value,
            "total_trades": stats.get('total_trades', 0),
            "win_rate": stats.get('win_rate', 0),
            "total_pnl": stats.get('total_pnl', 0),
            "best_trade": stats.get('best_trade', 0),
            "worst_trade": stats.get('worst_trade', 0),
            "last_signal": self.state.last_signal,
            "last_activity": self.state.last_activity.isoformat() if self.state.last_activity else None,
            "errors": self.state.errors,
            "interval": self.interval,
        }
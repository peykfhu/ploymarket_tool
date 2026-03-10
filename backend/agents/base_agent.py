
import asyncio

from abc import ABC, abstractmethod

from typing import Optional, List, Dict

from datetime import datetime

from models import Signal, AgentState, AgentStatus

from services.polymarket_client import polymarket_client

from services.risk_manager import risk_manager

from services.notifier import notifier

from database import db

from config import config

from utils.logger import get_logger





class BaseAgent(ABC):

    """基类 - 支持动态间隔、策略标记、大神级执行逻辑"""



    def __init__(self, name: str, interval_seconds: int = 90,

                 min_interval: int = 15, interval_setting_key: str = ""):

        self.name = name

        self._default_interval = interval_seconds

        self._min_interval = max(min_interval, config.MIN_SCAN_INTERVAL)

        self._interval_key = interval_setting_key

        self.logger = get_logger(f"agent.{name}")

        self.state = AgentState(name=name)

        self._running = False

        self._task: Optional[asyncio.Task] = None

        self.polymarket = polymarket_client



    @property

    def interval(self) -> int:

        """从数据库读取用户设置的间隔，强制最小值"""

        if self._interval_key:

            saved = db.get_setting(self._interval_key, self._default_interval)

            return max(int(saved), self._min_interval)

        return max(self._default_interval, self._min_interval)



    @abstractmethod

    async def scan_opportunities(self) -> List[Signal]:

        pass



    async def start(self):

        if self._running:

            return

        self._running = True

        self.state.status = AgentStatus.RUNNING

        self.logger.info(f"🚀 {self.name} 启动 (间隔={self.interval}s)")

        db.log_agent(self.name, "INFO", "启动")

        db.add_activity(self.name, "启动", f"扫描间隔 {self.interval}s", "🚀")

        self._task = asyncio.create_task(self._run_loop())



    async def stop(self):

        self._running = False

        self.state.status = AgentStatus.STOPPED

        if self._task:

            self._task.cancel()

            try:

                await self._task

            except asyncio.CancelledError:

                pass

        db.add_activity(self.name, "停止", "", "⏹")



    async def _run_loop(self):

        while self._running:

            try:

                self.state.last_activity = datetime.utcnow()

                self.state.scan_count += 1



                current_interval = self.interval

                db.add_activity(self.name, "扫描",

                                f"第{self.state.scan_count}次 (每{current_interval}s)", "🔍")



                signals = await self.scan_opportunities()



                if signals:

                    self.state.opportunities_found += len(signals)

                    db.add_activity(self.name, "发现",

                                    f"💡 {len(signals)}个机会", "💡")



                for signal in signals:

                    await self._process_signal(signal)



                await self._check_exits()



            except Exception as e:

                self.state.errors += 1

                self.logger.error(f"异常: {e}", exc_info=True)

                db.add_activity(self.name, "错误", str(e)[:80], "❌")

                if self.state.errors > 10:

                    self.state.status = AgentStatus.ERROR

                    await notifier.send_alert(f"⛔ {self.name} 错误过多")

                    self._running = False

                    break



            await asyncio.sleep(self.interval)



    async def _process_signal(self, signal: Signal):

        can_trade, reason = risk_manager.can_trade(signal)

        if not can_trade:

            db.add_activity(self.name, "风控", reason, "🛡️")

            return



        strategy = signal.metadata.get('strategy', 'info_arb')

        size = risk_manager.calculate_position_size(

            signal.edge, signal.confidence, strategy

        )



        if size < 0.5:

            return



        signal.size = size



        order = await self.polymarket.place_order(

            token_id=signal.market_id,

            side="BUY" if "BUY" in signal.direction else "SELL",

            price=signal.entry_price,

            size=signal.size

        )



        if order:

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

                'strategy': strategy,

                'metadata': signal.metadata,

            })



            self.state.total_trades += 1

            self.state.last_signal = signal.reasoning



            emoji = "🎯" if strategy == 'endgame' else "⚡"

            db.add_activity(self.name, "下单",

                            f"#{trade_id} [{strategy}] {signal.direction} ${size:.2f}@{signal.entry_price:.4f} edge={signal.edge:.2%}",

                            emoji)



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



    async def _check_exits(self):

        for pos in db.get_open_positions():

            if pos['agent_name'] != self.name:

                continue

            try:

                price = await self.polymarket.get_price(pos['market_id'])

                if price is None:

                    continue



                should_exit, reason = risk_manager.should_exit(pos, price)

                if should_exit:

                    if pos['direction'] in ('BUY_YES', 'BUY_NO'):

                        pnl = (price - pos['entry_price']) * pos['size']

                    else:

                        pnl = (pos['entry_price'] - price) * pos['size']



                    await self.polymarket.place_order(

                        token_id=pos['market_id'],

                        side="SELL" if "BUY" in pos['direction'] else "BUY",

                        price=price, size=pos['size']

                    )

                    db.close_trade(pos['id'], price, pnl)



                    if pnl > 0:

                        risk_manager.record_win()

                    else:

                        risk_manager.record_loss()



                    emoji = "💰" if pnl > 0 else "💸"

                    db.add_activity(self.name, "平仓",

                                    f"#{pos['id']} {reason} PnL=${pnl:.2f}", emoji)

            except Exception as e:

                self.logger.error(f"平仓检查异常: {e}")



    def get_state(self) -> Dict:

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

            "scan_count": self.state.scan_count,

            "opportunities_found": self.state.opportunities_found,

        }



"""

Agent-05: 尾盘确定性扫货 - 修复版



核心逻辑修正：

❌ 错误做法：看到任何 NO 价格 0.93 就买（这是赛季冠军市场，不是尾盘）

✅ 正确做法：只买 **即将在24小时内结算** 且 **一边价格 0.95-0.99** 的市场



关键区分：

- "Will Stars win Stanley Cup?" → 赛季冠军 → 还有几个月才结算 → 不碰

- "Will Lakers win tonight?" → 今晚比赛 → 比分锁定后买 → 这才是尾盘



额外条件：

- 必须在48小时内结算

- YES价格 0.95+ 才考虑买YES

- NO价格 0.95+ 才考虑买NO  

- 单笔最多 5% 仓位

"""

import asyncio

import time

from typing import List, Dict, Optional

from datetime import datetime, timedelta

from agents.base_agent import BaseAgent

from models import Signal

from services.polymarket_client import polymarket_client

from database import db

from utils.logger import get_logger



logger = get_logger("endgame_agent")



# 绝对不碰的关键词（赛季/锦标赛/长期市场）

BLACKLIST_KEYWORDS = [

    'stanley cup', 'world cup', 'super bowl', 'championship',

    'mvp', 'finals', 'season', 'annual', 'year',

    'before', 'by end of', 'by december', 'by january',

    'next president', 'win the 202', 'masters tournament',

    'oscar', 'grammy', 'nobel',

]





class EndgameAgent(BaseAgent):

    """Agent-05: 真正的尾盘扫货 — 只吃即将结算的确定性利润"""



    def __init__(self):

        super().__init__(

            name="Agent-05 尾盘扫货",

            interval_seconds=30,

            min_interval=15,

            interval_setting_key="interval_endgame"

        )

        self._scanned: set = set()



    async def scan_opportunities(self) -> List[Signal]:

        signals = []

        try:

            all_markets = await polymarket_client.get_active_markets(limit=500)

            if not all_markets:

                return signals



            # 只看48小时内结算的市场

            ending_soon = self._filter_ending_soon(all_markets)



            if ending_soon:

                db.add_activity(self.name, "扫描",

                    f"48h内结算: {len(ending_soon)} 个市场", "🎯")



                for m in ending_soon:

                    signal = self._analyze(m)

                    if signal:

                        signals.append(signal)

            else:

                db.add_activity(self.name, "扫描", "无即将结算市场", "⏳")



        except Exception as e:

            logger.error(f"尾盘异常: {e}", exc_info=True)

        return signals



    def _filter_ending_soon(self, markets: List[Dict]) -> List[Dict]:

        """只保留48小时内结算的市场"""

        now = datetime.utcnow()

        result = []



        for m in markets:

            mid = m.get('id', m.get('condition_id', ''))

            if mid in self._scanned:

                continue



            # 必须有结束时间

            end_str = (m.get('endDate') or m.get('end_date_iso')

                       or m.get('endDateIso') or m.get('close_time') or '')

            if not end_str:

                continue



            try:

                end_dt = datetime.fromisoformat(

                    str(end_str).replace('Z', '+00:00')

                ).replace(tzinfo=None)

                hours_left = (end_dt - now).total_seconds() / 3600



                # 核心：只要48小时内结算的

                if hours_left <= 0 or hours_left > 48:

                    continue



            except (ValueError, TypeError):

                continue



            # 排除长期市场（黑名单关键词）

            q = m.get('question', '').lower()

            if any(bw in q for bw in BLACKLIST_KEYWORDS):

                continue



            # 至少一边价格 >= 0.95（真正的尾盘确定性）

            yes_price = polymarket_client._extract_yes_price(m)

            no_price = polymarket_client.extract_no_price(m)



            sweet_yes = yes_price is not None and 0.95 <= yes_price <= 0.99

            sweet_no = no_price is not None and 0.95 <= no_price <= 0.99



            if not (sweet_yes or sweet_no):

                continue



            m['_yes'] = yes_price

            m['_no'] = no_price

            m['_hours_left'] = hours_left

            result.append(m)



        return result[:10]



    def _analyze(self, m: Dict) -> Optional[Signal]:

        mid = m.get('id', m.get('condition_id', ''))

        yes = m.get('_yes')

        no = m.get('_no')

        hours = m.get('_hours_left', 99)



        # 选最确定的一边（价格越高越确定）

        if yes and 0.95 <= yes <= 0.99:

            direction, entry, edge = "BUY_YES", yes, 1.0 - yes

            side = "YES"

        elif no and 0.95 <= no <= 0.99:

            direction, entry, edge = "BUY_NO", no, 1.0 - no

            side = "NO"

        else:

            return None



        # 利润太小不值得（<1%）

        if edge < 0.01:

            return None



        self._scanned.add(mid)

        if len(self._scanned) > 200:

            self._scanned.clear()



        confidence = min(0.99, entry + 0.01)



        return Signal(

            agent_name=self.name, market_id=mid,

            market_title=m.get('question', ''),

            direction=direction, entry_price=entry,

            fair_value=1.0, edge=edge, confidence=confidence, size=0,

            reasoning=(

                f"🎯 尾盘{side}: {entry:.2%}→100% (+{edge:.2%}) "

                f"{hours:.1f}h后结算"

            ),

            metadata={'strategy': 'endgame', 'hours_left': hours}

        )


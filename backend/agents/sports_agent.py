
import asyncio

import re

from typing import List, Dict, Optional

from agents.base_agent import BaseAgent

from models import Signal

from services.news_scraper import news_scraper

from services.polymarket_client import polymarket_client

from database import db

from utils.logger import get_logger



logger = get_logger("sports_agent")





class SportsAgent(BaseAgent):

    def __init__(self):

        super().__init__(name="Agent-04 伤病监控", interval_seconds=90,

                         min_interval=60, interval_setting_key="interval_sports")

        self.min_edge = 0.08



    async def scan_opportunities(self) -> List[Signal]:

        signals = []

        try:

            reports = await news_scraper.get_sports_injury_reports()

            if not reports:

                db.add_activity(self.name, "扫描", "无新伤病报告", "🏥")

                return signals



            db.add_activity(self.name, "数据", f"{len(reports)}条伤病", "🏥")



            markets = await polymarket_client.get_sports_markets(limit=50)

            if not markets: return signals



            for r in reports:

                for m in markets:

                    s = self._match(r, m)

                    if s: signals.append(s)

        except Exception as e:

            logger.error(f"体育扫描异常: {e}", exc_info=True)

        return signals



    def _match(self, report: Dict, market: Dict) -> Optional[Signal]:

        q = market.get('question', '').lower()

        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', report.get('title', ''))

        if not any(e.lower() in q for e in entities if len(e) > 2): return None



        mp = polymarket_client._extract_yes_price(market)

        if mp is None or mp <= 0.02 or mp >= 0.98: return None



        severity = report.get('severity', 'low')

        impact = {'critical': 0.20, 'high': 0.12, 'low': 0.05}.get(severity, 0.05)

        if impact < self.min_edge: return None



        mid = market.get('id', market.get('condition_id', ''))



        return Signal(

            agent_name=self.name, market_id=mid,

            market_title=market.get('question', ''),

            direction="BUY_NO", entry_price=1 - mp,

            fair_value=max(0.05, mp - impact), edge=impact,

            confidence=min(0.85, 0.5 + impact), size=0,

            reasoning=f"🏥 {report['title'][:50]} sev={severity}",

            metadata={'strategy': 'info_arb', 'severity': severity}

        )


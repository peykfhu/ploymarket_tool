
import asyncio

import re

from typing import List, Dict, Optional

from agents.base_agent import BaseAgent

from models import Signal

from services.binance_client import binance_client

from services.polymarket_client import polymarket_client

from database import db

from utils.logger import get_logger



logger = get_logger("crypto_agent")





class CryptoAgent(BaseAgent):

    def __init__(self):

        super().__init__(name="Agent-02 BTC差价猎人", interval_seconds=90,

                         min_interval=30, interval_setting_key="interval_crypto")

        self.min_spread = 0.03



    async def scan_opportunities(self) -> List[Signal]:

        signals = []

        try:

            btc_price = await binance_client.get_btc_price()

            if not btc_price:

                db.add_activity(self.name, "跳过", "无法获取BTC价格", "⚠️")

                return signals



            btc_stats = await binance_client.get_24h_stats("BTCUSDT")

            db.add_activity(self.name, "价格", f"BTC=${btc_price:,.0f}", "₿")



            # 使用修复后的方法

            btc_markets = await polymarket_client.get_crypto_markets(limit=50)

            if not btc_markets:

                db.add_activity(self.name, "无市场", "当前无活跃BTC市场", "⏳")

                return signals



            db.add_activity(self.name, "扫描", f"分析 {len(btc_markets)} 个加密市场", "🔍")



            for market in btc_markets:

                signal = self._analyze(market, btc_price, btc_stats)

                if signal:

                    signals.append(signal)



        except Exception as e:

            logger.error(f"BTC扫描异常: {e}", exc_info=True)

        return signals



    def _analyze(self, market: Dict, btc: float, stats: Optional[Dict]) -> Optional[Signal]:

        question = market.get('question', '')

        mp = polymarket_client._extract_yes_price(market)

        if mp is None or mp <= 0.02 or mp >= 0.98:

            return None



        target = self._extract_target(question)

        if target is None:

            return None



        vol = abs(stats.get('change_percent', 2)) / 100 if stats else 0.02

        ratio = btc / target



        if ratio > 1:

            fair = min(0.95, 0.7 + (ratio - 1) * 1.5)

        else:

            dist = (target - btc) / btc

            fair = max(0.05, 0.5 * (1 - min(dist / (vol * 5), 1)))



        edge = abs(fair - mp)

        if edge < self.min_spread:

            return None



        direction = "BUY_YES" if fair > mp else "BUY_NO"

        entry = mp if fair > mp else 1 - mp

        confidence = min(0.9, 0.5 + edge * 0.8)

        mid = market.get('id', market.get('condition_id', ''))



        return Signal(

            agent_name=self.name, market_id=mid, market_title=question,

            direction=direction, entry_price=entry, fair_value=fair,

            edge=edge, confidence=confidence, size=0,

            reasoning=f"₿ BTC=${btc:,.0f} T=${target:,.0f} M={mp:.2%} F={fair:.2%} E={edge:.2%}",

            metadata={'strategy': 'info_arb', 'btc': btc, 'target': target}

        )



    def _extract_target(self, q: str) -> Optional[float]:

        for p in [r'\$(\d{1,3}(?:,\d{3})+)', r'\$(\d+)[kK]']:

            m = re.search(p, q)

            if m:

                v = float(m.group(1).replace(',', ''))

                if v < 1000: v *= 1000

                return v

        return None


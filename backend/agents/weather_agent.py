
import asyncio

import time

from typing import List, Dict, Optional

from agents.base_agent import BaseAgent

from models import Signal

from services.noaa_client import noaa_client, MAJOR_CITIES

from services.polymarket_client import polymarket_client

from database import db

from utils.logger import get_logger



logger = get_logger("weather_agent")





class WeatherAgent(BaseAgent):

    """

    Agent-01: 气象狙击手



    修复版：

    1. 使用关键词精确匹配气候市场（不依赖错误的 tag_slug）

    2. 自动过滤已过期市场

    3. 只对真正的天气/气候问题下单

    """



    def __init__(self):

        super().__init__(

            name="Agent-01 气象狙击手",

            interval_seconds=600,

            min_interval=120,

            interval_setting_key="interval_weather"

        )

        self.min_edge = 0.08



    async def scan_opportunities(self) -> List[Signal]:

        signals = []

        try:

            # 获取气候市场（已修复：关键词精确匹配 + 过滤过期）

            climate_markets = await polymarket_client.get_climate_markets(limit=50)



            if not climate_markets:

                db.add_activity(self.name, "无市场",

                                "当前无活跃气候/天气市场", "🌤️")

                await self._log_noaa()

                return signals



            # 日志每个市场让用户看到

            for m in climate_markets[:5]:

                q = m.get('question', '')[:70]

                p = polymarket_client._extract_yes_price(m)

                db.add_activity(self.name, "气候市场",

                                f"{q}... YES={p:.2%}" if p else f"{q}...", "🌡️")



            db.add_activity(self.name, "扫描",

                            f"分析 {len(climate_markets)} 个气候市场", "🔍")



            # 对每个市场分析

            for market in climate_markets:

                market_signals = await self._analyze(market)

                signals.extend(market_signals)



        except Exception as e:

            logger.error(f"气象扫描异常: {e}", exc_info=True)



        return signals



    async def _analyze(self, market: Dict) -> List[Signal]:

        """分析单个气候市场"""

        signals = []

        question = market.get('question', '')

        q_lower = question.lower()

        market_price = polymarket_client._extract_yes_price(market)



        if market_price is None or market_price <= 0.03 or market_price >= 0.97:

            return signals



        # 确认是真正的天气/气候问题

        weather_words = ['temperature', 'rain', 'snow', 'storm', 'weather',

                          'heat', 'cold', 'hurricane', 'tornado', 'flood',

                          'celsius', 'fahrenheit', 'degree', 'precipitation',

                          'hottest', 'coldest', 'warmest', 'drought', 'wildfire',

                          'forecast', 'noaa']



        is_weather = any(w in q_lower for w in weather_words)



        if not is_weather:

            # 不是天气问题，检查是否是气候变化大问题

            climate_words = ['climate', 'global warming', 'carbon', 'emissions',

                              'arctic', 'sea level', 'el nino', 'la nina']

            is_climate = any(w in q_lower for w in climate_words)

            if not is_climate:

                return signals  # 既不是天气也不是气候，跳过



        # 尝试匹配城市

        matched_city = None

        for city in MAJOR_CITIES:

            if city.lower() in q_lower:

                matched_city = city

                break



        if matched_city:

            # 有城市 → 用 NOAA 数据对比

            try:

                weather = await noaa_client.get_precipitation_probability(matched_city)

                if weather and any(w in q_lower for w in ['rain', 'precipitation', 'storm', 'snow']):

                    noaa_prob = weather['max_probability'] / 100

                    signals.extend(self._compare_prob(

                        market, market_price, noaa_prob, matched_city, weather

                    ))

            except Exception as e:

                logger.error(f"NOAA {matched_city}: {e}")

        else:

            # 无匹配城市 → 记录市场信息供用户参考

            db.add_activity(self.name, "发现",

                            f"气候市场: {question[:60]}... 价格={market_price:.2%}（无NOAA匹配）", "🌍")



        return signals



    def _compare_prob(self, market: Dict, market_price: float,

                       noaa_prob: float, city: str, weather: Dict) -> List[Signal]:

        """NOAA vs Market 概率对比"""

        signals = []

        mid = self._get_id(market)



        if noaa_prob > market_price + self.min_edge:

            edge = noaa_prob - market_price

            signals.append(Signal(

                agent_name=self.name, market_id=mid,

                market_title=market.get('question', ''),

                direction="BUY_YES", entry_price=market_price,

                fair_value=noaa_prob, edge=edge,

                confidence=min(0.95, noaa_prob * 0.98), size=0,

                reasoning=f"🌧 {city}: NOAA={noaa_prob:.0%} PM={market_price:.0%} +{edge:.0%}",

                metadata={'strategy': 'info_arb', 'city': city,

                          'noaa_prob': noaa_prob}

            ))

            db.add_activity(self.name, "信号",

                            f"🌧 {city} NOAA={noaa_prob:.0%} > PM={market_price:.0%}", "💡")



        elif market_price > noaa_prob + self.min_edge:

            edge = market_price - noaa_prob

            signals.append(Signal(

                agent_name=self.name, market_id=mid,

                market_title=market.get('question', ''),

                direction="BUY_NO", entry_price=1 - market_price,

                fair_value=1 - noaa_prob, edge=edge,

                confidence=min(0.95, (1 - noaa_prob) * 0.98), size=0,

                reasoning=f"☀️ {city}: NOAA={noaa_prob:.0%} PM高估={market_price:.0%} +{edge:.0%}",

                metadata={'strategy': 'info_arb', 'city': city,

                          'noaa_prob': noaa_prob}

            ))



        return signals



    async def _log_noaa(self):

        """没有市场时也记录NOAA数据"""

        try:

            for city in list(MAJOR_CITIES.keys())[:3]:

                w = await noaa_client.get_precipitation_probability(city)

                if w:

                    db.add_activity(self.name, "NOAA数据",

                                    f"{city}: 降雨{w['max_probability']}%", "🛰️")

                await asyncio.sleep(1)

        except:

            pass



    def _get_id(self, m: Dict) -> str:

        return m.get('id', m.get('condition_id', m.get('questionID', '')))


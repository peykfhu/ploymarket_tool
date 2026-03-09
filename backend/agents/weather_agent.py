# backend/agents/weather_agent.py
import asyncio
from typing import List
from agents.base_agent import BaseAgent
from models import Signal
from services.noaa_client import noaa_client, MAJOR_CITIES
from services.polymarket_client import polymarket_client
from utils.logger import get_logger

logger = get_logger("weather_agent")


class WeatherAgent(BaseAgent):
    """
    Agent-01: 气象狙击手

    每10分钟刷NOAA预报，对比Polymarket天气合约定价。
    当NOAA降雨概率显著高于/低于市场定价时入场。
    """

    def __init__(self):
        super().__init__(
            name="Agent-01 气象狙击手",
            interval_seconds=600  # 10分钟
        )
        self.min_edge = 0.08  # 最小8%边际

    async def scan_opportunities(self) -> List[Signal]:
        signals = []

        try:
            # 1. 获取NOAA所有城市的天气数据
            weather_data = await noaa_client.scan_all_cities()
            logger.info(f"扫描了 {len(weather_data)} 个城市的天气数据")

            # 2. 获取Polymarket上的天气相关市场
            weather_markets = await self._find_weather_markets()
            logger.info(f"找到 {len(weather_markets)} 个天气市场")

            # 3. 对比寻找定价偏差
            for city_data in weather_data:
                city = city_data['city']
                noaa_rain_prob = city_data['max_probability'] / 100  # 转为0-1

                # 寻找匹配的Polymarket市场
                for market in weather_markets:
                    if city.lower() in market.get('question', '').lower():
                        market_price = self._get_market_price(market)
                        if market_price is None:
                            continue

                        # 计算边际
                        if noaa_rain_prob > market_price:
                            # NOAA说会下雨但市场低估 -> 买YES
                            edge = noaa_rain_prob - market_price
                            if edge >= self.min_edge:
                                confidence = min(noaa_rain_prob, 0.95)
                                signals.append(Signal(
                                    agent_name=self.name,
                                    market_id=market.get('id', ''),
                                    market_title=market.get('question', ''),
                                    direction="BUY_YES",
                                    entry_price=market_price,
                                    fair_value=noaa_rain_prob,
                                    edge=edge,
                                    confidence=confidence,
                                    size=0,  # will be calculated by risk manager
                                    reasoning=(
                                        f"NOAA预报{city}降雨概率{noaa_rain_prob:.0%}，"
                                        f"市场价{market_price:.0%}，"
                                        f"边际{edge:.0%}"
                                    ),
                                    metadata={
                                        "city": city,
                                        "noaa_prob": noaa_rain_prob,
                                        "market_price": market_price,
                                        "noaa_confidence": city_data['noaa_confidence'],
                                        "periods_analyzed": city_data['hours_analyzed']
                                    }
                                ))
                                logger.info(
                                    f"🌧 发现机会: {city} NOAA={noaa_rain_prob:.0%} "
                                    f"Market={market_price:.0%} Edge={edge:.0%}"
                                )

                        elif market_price > noaa_rain_prob + self.min_edge:
                            # 市场高估 -> 买NO
                            edge = market_price - noaa_rain_prob
                            if edge >= self.min_edge:
                                confidence = min(1 - noaa_rain_prob, 0.95)
                                signals.append(Signal(
                                    agent_name=self.name,
                                    market_id=market.get('id', ''),
                                    market_title=market.get('question', ''),
                                    direction="BUY_NO",
                                    entry_price=1 - market_price,
                                    fair_value=1 - noaa_rain_prob,
                                    edge=edge,
                                    confidence=confidence,
                                    size=0,
                                    reasoning=(
                                        f"NOAA预报{city}降雨概率仅{noaa_rain_prob:.0%}，"
                                        f"市场高估为{market_price:.0%}，"
                                        f"买NO边际{edge:.0%}"
                                    ),
                                    metadata={
                                        "city": city,
                                        "noaa_prob": noaa_rain_prob,
                                        "market_price": market_price,
                                    }
                                ))

        except Exception as e:
            logger.error(f"扫描天气机会异常: {e}", exc_info=True)

        return signals

    async def _find_weather_markets(self) -> List[dict]:
        """查找Polymarket上的天气相关市场"""
        try:
            all_markets = await polymarket_client.get_markets(limit=200)
            weather_keywords = [
                'rain', 'weather', 'temperature', 'snow', 'storm',
                'hurricane', 'tornado', 'forecast', 'precipitation'
            ]
            weather_markets = []
            for m in all_markets:
                question = m.get('question', '').lower()
                if any(kw in question for kw in weather_keywords):
                    weather_markets.append(m)
            return weather_markets
        except Exception as e:
            logger.error(f"查找天气市场异常: {e}")
            return []

    def _get_market_price(self, market: dict) -> float | None:
        """从市场数据中提取当前YES价格"""
        try:
            # Polymarket API 格式可能不同，适配多种格式
            if 'tokens' in market:
                for token in market['tokens']:
                    if token.get('outcome') == 'Yes':
                        return float(token.get('price', 0))

            if 'outcomePrices' in market:
                prices = market['outcomePrices']
                if isinstance(prices, list) and len(prices) > 0:
                    return float(prices[0])
                if isinstance(prices, str):
                    import json
                    prices = json.loads(prices)
                    return float(prices[0]) if prices else None

            if 'bestBid' in market:
                return float(market['bestBid'])

            return None
        except (ValueError, IndexError, KeyError):
            return None
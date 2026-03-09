# backend/agents/crypto_agent.py
import asyncio
from typing import List
from agents.base_agent import BaseAgent
from models import Signal
from services.binance_client import binance_client
from services.polymarket_client import polymarket_client
from utils.logger import get_logger

logger = get_logger("crypto_agent")


class CryptoAgent(BaseAgent):
    """
    Agent-02: 比特币差价猎人

    同时监控Binance和Polymarket上的BTC价格合约。
    差价超过阈值时进行套利。
    """

    def __init__(self):
        super().__init__(
            name="Agent-02 BTC差价猎人",
            interval_seconds=120  # 2分钟
        )
        self.min_spread = 0.03  # 最小3%差价

    async def scan_opportunities(self) -> List[Signal]:
        signals = []

        try:
            # 1. 获取Binance上的BTC真实价格
            btc_price = await binance_client.get_btc_price()
            if btc_price is None:
                logger.warning("无法获取BTC价格")
                return signals

            btc_stats = await binance_client.get_24h_stats("BTCUSDT")
            logger.info(f"BTC现价: ${btc_price:,.2f}")

            # 2. 获取Polymarket上的BTC相关市场
            btc_markets = await self._find_btc_markets()
            logger.info(f"找到 {len(btc_markets)} 个BTC相关市场")

            # 3. 分析每个市场
            for market in btc_markets:
                signal = await self._analyze_btc_market(market, btc_price, btc_stats)
                if signal:
                    signals.append(signal)

        except Exception as e:
            logger.error(f"扫描BTC套利机会异常: {e}", exc_info=True)

        return signals

    async def _find_btc_markets(self) -> List[dict]:
        """查找BTC相关的预测市场"""
        try:
            all_markets = await polymarket_client.get_markets(limit=200)
            btc_keywords = [
                'bitcoin', 'btc', 'crypto',
                'bitcoin price', 'btc price',
                'bitcoin above', 'bitcoin below'
            ]
            btc_markets = []
            for m in all_markets:
                question = m.get('question', '').lower()
                if any(kw in question for kw in btc_keywords):
                    btc_markets.append(m)
            return btc_markets
        except Exception as e:
            logger.error(f"查找BTC市场异常: {e}")
            return []

    async def _analyze_btc_market(self, market: dict,
                                  btc_price: float,
                                  btc_stats: dict) -> Signal | None:
        """分析单个BTC市场是否存在套利机会"""
        question = market.get('question', '')
        market_price = self._get_market_price(market)

        if market_price is None:
            return None

        # 解析目标价格（例如 "Will Bitcoin be above $100,000 by..."）
        target_price = self._extract_target_price(question)
        if target_price is None:
            return None

        # 计算实际概率（简化模型：基于当前价格与目标价格的距离）
        price_ratio = btc_price / target_price

        if price_ratio > 1:
            # BTC已经高于目标价 -> YES的公允价值应该很高
            fair_value = min(0.95, 0.5 + (price_ratio - 1) * 2)
        else:
            # BTC低于目标价 -> 需要考虑时间和波动率
            distance = (target_price - btc_price) / btc_price
            if btc_stats:
                daily_vol = abs(btc_stats.get('change_percent', 2)) / 100
            else:
                daily_vol = 0.02  # 默认2%日波动

            # 简化：距离越大越不可能到达
            fair_value = max(0.05, 0.5 - distance / (daily_vol * 10))

        # 计算边际
        edge = abs(fair_value - market_price)

        if edge >= self.min_spread:
            if fair_value > market_price:
                direction = "BUY_YES"
                entry_price = market_price
            else:
                direction = "BUY_NO"
                entry_price = 1 - market_price

            confidence = min(0.9, 0.5 + edge)

            logger.info(
                f"₿ BTC套利机会: {question[:60]}... "
                f"Market={market_price:.2%} Fair={fair_value:.2%} "
                f"Edge={edge:.2%}"
            )

            return Signal(
                agent_name=self.name,
                market_id=market.get('id', ''),
                market_title=question,
                direction=direction,
                entry_price=entry_price,
                fair_value=fair_value,
                edge=edge,
                confidence=confidence,
                size=0,
                reasoning=(
                    f"BTC=${btc_price:,.0f}, 目标=${target_price:,.0f}, "
                    f"市场价={market_price:.2%}, 公允={fair_value:.2%}, "
                    f"边际={edge:.2%}"
                ),
                metadata={
                    "btc_price": btc_price,
                    "target_price": target_price,
                    "price_ratio": price_ratio,
                    "market_price": market_price,
                    "fair_value": fair_value,
                }
            )

        return None

    def _extract_target_price(self, question: str) -> float | None:
        """从问题中提取目标价格"""
        import re
        # 匹配 $XXX,XXX 或 $XXXK 格式
        patterns = [
            r'\$(\d{1,3}(?:,\d{3})+)',  # $100,000
            r'\$(\d+)[kK]',  # $100K
            r'\$(\d+(?:\.\d+)?)\s*(?:thousand|k)',  # $100 thousand
        ]

        for pattern in patterns:
            match = re.search(pattern, question)
            if match:
                price_str = match.group(1).replace(',', '')
                price = float(price_str)
                if 'k' in question[match.end() - 1:match.end() + 1].lower():
                    price *= 1000
                if price < 1000:  # 可能是K格式
                    price *= 1000
                return price

        return None

    def _get_market_price(self, market: dict) -> float | None:
        """提取市场YES价格"""
        try:
            if 'tokens' in market:
                for token in market['tokens']:
                    if token.get('outcome') == 'Yes':
                        return float(token.get('price', 0))
            if 'outcomePrices' in market:
                prices = market['outcomePrices']
                if isinstance(prices, list) and prices:
                    return float(prices[0])
            return None
        except (ValueError, IndexError):
            return None
# backend/agents/politics_agent.py
import asyncio
from typing import List
from agents.base_agent import BaseAgent
from models import Signal
from services.news_scraper import news_scraper
from services.polymarket_client import polymarket_client
from utils.logger import get_logger

logger = get_logger("politics_agent")


class PoliticsAgent(BaseAgent):
    """
    Agent-03: 政治民调收割机

    爬取民调机构数据，找出市场反应滞后的政治合约。
    """

    def __init__(self):
        super().__init__(
            name="Agent-03 民调收割机",
            interval_seconds=900  # 15分钟
        )
        self.min_edge = 0.10  # 政治市场需要更大边际

    async def scan_opportunities(self) -> List[Signal]:
        signals = []

        try:
            # 1. 获取最新政治新闻和民调
            news = await news_scraper.get_political_news("election poll survey")
            polls = await news_scraper.get_poll_data()

            logger.info(f"获取 {len(news)} 条政治新闻, {len(polls)} 条民调数据")

            # 2. 获取政治类市场
            political_markets = await self._find_political_markets()
            logger.info(f"找到 {len(political_markets)} 个政治市场")

            # 3. 分析情绪并寻找机会
            sentiment_scores = self._analyze_sentiment(news)

            for market in political_markets:
                signal = self._evaluate_market(market, sentiment_scores, polls)
                if signal:
                    signals.append(signal)

        except Exception as e:
            logger.error(f"扫描政治套利异常: {e}", exc_info=True)

        return signals

    async def _find_political_markets(self) -> List[dict]:
        """查找政治类市场"""
        try:
            all_markets = await polymarket_client.get_markets(limit=200)
            political_keywords = [
                'election', 'president', 'senate', 'congress',
                'vote', 'poll', 'democrat', 'republican',
                'governor', 'primary', 'nomination', 'cabinet',
                'trump', 'biden', 'political', 'party'
            ]
            return [
                m for m in all_markets
                if any(kw in m.get('question', '').lower()
                       for kw in political_keywords)
            ]
        except Exception as e:
            logger.error(f"查找政治市场异常: {e}")
            return []

    def _analyze_sentiment(self, news: List[dict]) -> dict:
        """分析新闻情绪"""
        entity_sentiment = {}

        political_entities = [
            'trump', 'biden', 'harris', 'desantis', 'republican',
            'democrat', 'gop', 'dnc', 'rnc'
        ]

        for article in news:
            title = article.get('title', '').lower()
            sentiment = article.get('sentiment', 'neutral')

            for entity in political_entities:
                if entity in title:
                    if entity not in entity_sentiment:
                        entity_sentiment[entity] = {
                            'positive': 0, 'negative': 0, 'neutral': 0,
                            'total': 0
                        }
                    entity_sentiment[entity][sentiment] += 1
                    entity_sentiment[entity]['total'] += 1

        # 计算情绪分数 (-1 到 1)
        for entity in entity_sentiment:
            data = entity_sentiment[entity]
            if data['total'] > 0:
                data['score'] = (
                        (data['positive'] - data['negative']) / data['total']
                )
            else:
                data['score'] = 0

        return entity_sentiment

    def _evaluate_market(self, market: dict, sentiment: dict,
                         polls: List[dict]) -> Signal | None:
        """评估单个政治市场"""
        question = market.get('question', '').lower()
        market_price = self._get_market_price(market)

        if market_price is None or market_price <= 0.01 or market_price >= 0.99:
            return None

        # 查找相关实体的情绪
        relevant_sentiment = None
        matched_entity = None

        for entity, data in sentiment.items():
            if entity in question and data['total'] >= 3:
                relevant_sentiment = data
                matched_entity = entity
                break

        if not relevant_sentiment:
            return None

        score = relevant_sentiment['score']

        # 将情绪分数转换为公允价值调整
        # 正面情绪 -> YES价值应该更高
        sentiment_adjustment = score * 0.15  # 最大15%调整
        fair_value = min(0.95, max(0.05, market_price + sentiment_adjustment))

        edge = abs(fair_value - market_price)

        if edge >= self.min_edge:
            if fair_value > market_price:
                direction = "BUY_YES"
                entry_price = market_price
            else:
                direction = "BUY_NO"
                entry_price = 1 - market_price

            confidence = min(0.85, 0.5 + edge * 0.5)

            news_count = relevant_sentiment['total']

            logger.info(
                f"🏛 政治机会: {market.get('question', '')[:60]}... "
                f"Entity={matched_entity} Sentiment={score:.2f} "
                f"Edge={edge:.2%}"
            )

            return Signal(
                agent_name=self.name,
                market_id=market.get('id', ''),
                market_title=market.get('question', ''),
                direction=direction,
                entry_price=entry_price,
                fair_value=fair_value,
                edge=edge,
                confidence=confidence,
                size=0,
                reasoning=(
                    f"[{matched_entity}] 情绪分={score:.2f} "
                    f"({news_count}条新闻), "
                    f"市场={market_price:.2%} -> 公允={fair_value:.2%} "
                    f"边际={edge:.2%}"
                ),
                metadata={
                    "entity": matched_entity,
                    "sentiment_score": score,
                    "news_count": news_count,
                    "sentiment_data": relevant_sentiment,
                }
            )

        return None

    def _get_market_price(self, market: dict) -> float | None:
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
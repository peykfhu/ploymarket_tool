# backend/agents/sports_agent.py
import asyncio
from typing import List
from agents.base_agent import BaseAgent
from models import Signal
from services.news_scraper import news_scraper
from services.polymarket_client import polymarket_client
from utils.logger import get_logger

logger = get_logger("sports_agent")


class SportsAgent(BaseAgent):
    """
    Agent-04: 体育伤病监控

    实时扫描体育媒体伤病报告，
    看到关键球员伤停，捕捉赔率定价偏差。
    """

    def __init__(self):
        super().__init__(
            name="Agent-04 伤病监控",
            interval_seconds=300  # 5分钟
        )
        self.min_edge = 0.08

    async def scan_opportunities(self) -> List[Signal]:
        signals = []

        try:
            # 1. 获取最新伤病报告
            injury_reports = await news_scraper.get_sports_injury_reports()
            logger.info(f"获取 {len(injury_reports)} 条伤病报告")

            if not injury_reports:
                return signals

            # 2. 获取体育类市场
            sports_markets = await self._find_sports_markets()
            logger.info(f"找到 {len(sports_markets)} 个体育市场")

            # 3. 交叉对比
            for report in injury_reports:
                for market in sports_markets:
                    signal = self._match_injury_to_market(report, market)
                    if signal:
                        signals.append(signal)

        except Exception as e:
            logger.error(f"扫描体育伤病异常: {e}", exc_info=True)

        return signals

    async def _find_sports_markets(self) -> List[dict]:
        """查找体育类市场"""
        try:
            all_markets = await polymarket_client.get_markets(limit=200)
            sports_keywords = [
                'nba', 'nfl', 'mlb', 'nhl', 'soccer', 'football',
                'basketball', 'baseball', 'championship', 'playoff',
                'super bowl', 'world series', 'finals', 'mvp',
                'win', 'game', 'match', 'series', 'season'
            ]
            return [
                m for m in all_markets
                if any(kw in m.get('question', '').lower()
                       for kw in sports_keywords)
            ]
        except Exception as e:
            logger.error(f"查找体育市场异常: {e}")
            return []

    def _match_injury_to_market(self, report: dict,
                                market: dict) -> Signal | None:
        """将伤病报告匹配到市场"""
        question = market.get('question', '').lower()
        injury_title = report.get('title', '').lower()
        severity = report.get('severity', 'low')

        # 提取球队/球员名
        teams_players = self._extract_entities(injury_title)

        # 检查是否与市场相关
        matched = False
        for entity in teams_players:
            if entity.lower() in question:
                matched = True
                break

        if not matched:
            return None

        market_price = self._get_market_price(market)
        if market_price is None or market_price <= 0.02 or market_price >= 0.98:
            return None

        # 根据伤病严重程度估算影响
        severity_impact = {
            'critical': 0.20,  # 赛季报销级别
            'high': 0.12,  # 数周缺席
            'low': 0.05,  # 日常管理
        }

        impact = severity_impact.get(severity, 0.05)

        # 判断伤病对市场的影响方向
        # 关键球员受伤 -> 该队赢的概率降低
        # 简化逻辑：如果伤病球员在question中与YES方向相关
        if any(entity.lower() in question for entity in teams_players):
            fair_value = max(0.05, market_price - impact)
            direction = "BUY_NO"
            entry_price = 1 - market_price
            edge = impact
        else:
            return None

        if edge < self.min_edge:
            return None

        confidence = min(0.85, 0.5 + edge)

        logger.info(
            f"🏥 伤病机会: {report['title'][:60]}... "
            f"Severity={severity} Impact={impact:.2%} Edge={edge:.2%}"
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
                f"伤病报告: {report['title'][:80]}, "
                f"严重程度={severity}, 影响={impact:.2%}, "
                f"市场调整={edge:.2%}"
            ),
            metadata={
                "injury_report": report,
                "severity": severity,
                "impact": impact,
                "matched_entities": teams_players,
            }
        )

    def _extract_entities(self, text: str) -> List[str]:
        """从伤病报告中提取球队/球员名"""
        import re
        # 提取大写开头的词（可能是人名/队名）
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)

        # 已知球队
        known_teams = [
            'Lakers', 'Celtics', 'Warriors', 'Bulls', 'Heat',
            'Knicks', 'Nets', 'Bucks', 'Suns', 'Mavericks',
            'Chiefs', 'Eagles', 'Cowboys', 'Patriots', '49ers',
            'Yankees', 'Dodgers', 'Red Sox', 'Cubs', 'Mets',
        ]

        entities = []
        for word in words:
            if len(word) > 2:
                entities.append(word)

        return entities

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
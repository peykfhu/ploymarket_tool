
import asyncio

from typing import List, Dict, Optional

from agents.base_agent import BaseAgent

from models import Signal

from services.news_scraper import news_scraper

from services.polymarket_client import polymarket_client

from database import db

from utils.logger import get_logger



logger = get_logger("politics_agent")





class PoliticsAgent(BaseAgent):

    def __init__(self):

        super().__init__(name="Agent-03 民调收割机", interval_seconds=90,

                         min_interval=60, interval_setting_key="interval_politics")

        self.min_edge = 0.10



    async def scan_opportunities(self) -> List[Signal]:

        signals = []

        try:

            news = await news_scraper.get_political_news("election poll")

            db.add_activity(self.name, "新闻", f"{len(news)}条", "📰")



            markets = await polymarket_client.get_politics_markets(limit=50)

            if not markets:

                db.add_activity(self.name, "无市场", "当前无活跃政治市场", "⏳")

                return signals



            db.add_activity(self.name, "扫描", f"{len(markets)} 个政治市场", "🔍")

            sentiment = self._analyze_sentiment(news)



            for m in markets:

                s = self._evaluate(m, sentiment)

                if s: signals.append(s)

        except Exception as e:

            logger.error(f"政治扫描异常: {e}", exc_info=True)

        return signals



    def _analyze_sentiment(self, news: List[Dict]) -> Dict:

        entities = ['trump', 'biden', 'harris', 'desantis', 'republican', 'democrat']

        scores = {}

        for a in news:

            t = a.get('title', '').lower()

            s = a.get('sentiment', 'neutral')

            for e in entities:

                if e in t:

                    if e not in scores:

                        scores[e] = {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0}

                    scores[e][s] += 1

                    scores[e]['total'] += 1

        for e in scores:

            d = scores[e]

            d['score'] = (d['positive'] - d['negative']) / d['total'] if d['total'] > 0 else 0

        return scores



    def _evaluate(self, market: Dict, sentiment: Dict) -> Optional[Signal]:

        q = market.get('question', '').lower()

        mp = polymarket_client._extract_yes_price(market)

        if mp is None or mp <= 0.02 or mp >= 0.98: return None



        matched = None

        for e, d in sentiment.items():

            if e in q and d['total'] >= 3:

                matched = e; break

        if not matched: return None



        score = sentiment[matched]['score']

        fair = min(0.95, max(0.05, mp + score * 0.12))

        edge = abs(fair - mp)

        if edge < self.min_edge: return None



        direction = "BUY_YES" if fair > mp else "BUY_NO"

        entry = mp if fair > mp else 1 - mp

        mid = market.get('id', market.get('condition_id', ''))



        return Signal(

            agent_name=self.name, market_id=mid,

            market_title=market.get('question', ''),

            direction=direction, entry_price=entry, fair_value=fair,

            edge=edge, confidence=min(0.85, 0.5 + edge * 0.5), size=0,

            reasoning=f"🏛 [{matched}] sent={score:.2f} M={mp:.2%} F={fair:.2%} E={edge:.2%}",

            metadata={'strategy': 'info_arb', 'entity': matched}

        )


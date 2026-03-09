# backend/services/news_scraper.py
import aiohttp
import asyncio
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from config import config
from utils.logger import get_logger

logger = get_logger("news_scraper")


class NewsScraper:
    """新闻和社交媒体数据抓取"""

    def __init__(self):
        self.newsapi_key = config.NEWSAPI_KEY
        self.twitter_token = config.TWITTER_BEARER_TOKEN
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session

    async def get_political_news(self, query: str = "election poll") -> List[Dict]:
        """获取政治新闻"""
        if not self.newsapi_key:
            return await self._get_free_news(query)

        session = await self._get_session()
        try:
            async with session.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 20,
                    "apiKey": self.newsapi_key,
                }
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    articles = data.get("articles", [])
                    return [{
                        "title": a["title"],
                        "description": a.get("description", ""),
                        "source": a["source"]["name"],
                        "published_at": a["publishedAt"],
                        "url": a["url"],
                        "sentiment": self._quick_sentiment(
                            f"{a['title']} {a.get('description', '')}"
                        )
                    } for a in articles]
                return []
        except Exception as e:
            logger.error(f"获取政治新闻异常: {e}")
            return []

    async def get_sports_injury_reports(self) -> List[Dict]:
        """获取体育伤病报告"""
        sources = [
            ("ESPN Injury", "https://newsapi.org/v2/everything"),
            ("Sports Injury", "https://newsapi.org/v2/everything"),
        ]

        all_reports = []
        session = await self._get_session()

        queries = [
            "NBA injury report",
            "NFL injury update",
            "MLB injury news",
            "player injured out",
        ]

        for query in queries:
            try:
                if self.newsapi_key:
                    async with session.get(
                        "https://newsapi.org/v2/everything",
                        params={
                            "q": query,
                            "language": "en",
                            "sortBy": "publishedAt",
                            "pageSize": 10,
                            "apiKey": self.newsapi_key,
                        }
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for a in data.get("articles", []):
                                injury_info = self._extract_injury_info(
                                    a["title"], a.get("description", "")
                                )
                                if injury_info:
                                    all_reports.append({
                                        **injury_info,
                                        "source": a["source"]["name"],
                                        "published_at": a["publishedAt"],
                                        "url": a["url"],
                                    })
            except Exception as e:
                logger.error(f"获取伤病报告异常: {e}")

        return all_reports

    async def get_poll_data(self) -> List[Dict]:
        """获取民调数据"""
        polls = []

        # RealClearPolitics / FiveThirtyEight 模拟数据获取
        # 实际部署时需要适配真实数据源
        session = await self._get_session()

        try:
            if self.newsapi_key:
                async with session.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": "poll survey approval rating",
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": 20,
                        "apiKey": self.newsapi_key,
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for a in data.get("articles", []):
                            poll_info = self._extract_poll_data(
                                a["title"], a.get("description", "")
                            )
                            if poll_info:
                                polls.append({
                                    **poll_info,
                                    "source": a["source"]["name"],
                                    "published_at": a["publishedAt"],
                                })
        except Exception as e:
            logger.error(f"获取民调数据异常: {e}")

        return polls

    async def _get_free_news(self, query: str) -> List[Dict]:
        """使用免费新闻源"""
        session = await self._get_session()
        try:
            # 使用 Google News RSS
            async with session.get(
                f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    # 简单的 XML 解析
                    items = re.findall(
                        r'<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?<pubDate>(.*?)</pubDate>.*?</item>',
                        text, re.DOTALL
                    )
                    return [{
                        "title": title.replace('<![CDATA[', '').replace(']]>', ''),
                        "description": "",
                        "source": "Google News",
                        "published_at": pub_date,
                        "url": link,
                        "sentiment": self._quick_sentiment(title)
                    } for title, link, pub_date in items[:20]]
                return []
        except Exception as e:
            logger.error(f"获取免费新闻异常: {e}")
            return []

    def _quick_sentiment(self, text: str) -> str:
        """快速情绪分析（基于关键词）"""
        text_lower = text.lower()
        positive_words = [
            'win', 'surge', 'lead', 'ahead', 'gain', 'rally', 'boost',
            'strong', 'victory', 'success', 'up', 'rise', 'positive'
        ]
        negative_words = [
            'lose', 'fall', 'drop', 'behind', 'decline', 'crash', 'weak',
            'defeat', 'fail', 'down', 'plunge', 'negative', 'concern'
        ]

        pos = sum(1 for w in positive_words if w in text_lower)
        neg = sum(1 for w in negative_words if w in text_lower)

        if pos > neg:
            return "positive"
        elif neg > pos:
            return "negative"
        return "neutral"

    def _extract_injury_info(self, title: str, description: str) -> Optional[Dict]:
        """从新闻中提取伤病信息"""
        text = f"{title} {description}".lower()

        injury_keywords = [
            'injured', 'injury', 'out for', 'sidelined', 'sprain',
            'fracture', 'torn', 'surgery', 'concussion', 'hamstring',
            'questionable', 'doubtful', 'ruled out', 'day-to-day'
        ]

        if any(kw in text for kw in injury_keywords):
            severity = "high"
            if any(w in text for w in ['torn', 'fracture', 'surgery', 'season']):
                severity = "critical"
            elif any(w in text for w in ['day-to-day', 'questionable', 'minor']):
                severity = "low"

            return {
                "title": title,
                "description": description,
                "severity": severity,
                "is_injury": True,
            }
        return None

    def _extract_poll_data(self, title: str, description: str) -> Optional[Dict]:
        """从新闻中提取民调数据"""
        text = f"{title} {description}"

        # 尝试提取百分比数字
        percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', text)
        if percentages:
            return {
                "title": title,
                "percentages": [float(p) for p in percentages],
                "sentiment": self._quick_sentiment(text),
            }
        return None

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


news_scraper = NewsScraper()
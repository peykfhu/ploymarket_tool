
"""

Agent-06: 体育尾盘扫货 — 大赛专用（NBA/英超/NFL）



正确策略：

1. 拉实时比分 → 检测比赛已锁定

2. NBA: Q4 领先15+ 或 比赛结束

3. 足球: 终场哨(FT) 且有进球领先

4. NFL: Q4 领先14+

5. 匹配 Polymarket 上"今晚X会赢吗"类型市场

6. 价格 0.92-0.98 → 买确定一边

7. 不碰赛季冠军市场！



排除：

- "Will X win Stanley Cup/World Cup/Championship" → 这是长期市场不是尾盘

- 任何截止日期超过7天的 → 不是单场比赛

"""

import asyncio

import re

from typing import List, Dict, Optional

from datetime import datetime, timedelta

from agents.base_agent import BaseAgent

from models import Signal

from services.polymarket_client import polymarket_client

from services.sports_live import sports_live

from database import db

from utils.logger import get_logger



logger = get_logger("sports_endgame")



# 赛季/锦标赛黑名单 — 这些不是单场比赛

SEASON_BLACKLIST = [

    'stanley cup', 'world cup', 'super bowl', 'championship',

    'win the 2025', 'win the 2026', 'win the 2027',

    'mvp', 'finals', 'season', 'playoff', 'title',

    'masters tournament', 'grand slam', 'world series',

    'ballon d\'or', 'golden boot', 'scoring title',

]



# 单场比赛关键词

SINGLE_GAME_KEYWORDS = [

    'win game', 'beat', 'tonight', 'today', 'this week',

    'matchday', 'game day', 'vs', 'versus', 'match',

    'round of', 'leg', 'fixture',

]





class SportsEndgameAgent(BaseAgent):

    """Agent-06: 体育尾盘 — 只吃实时比分确认的单场比赛"""



    def __init__(self):

        super().__init__(

            name="Agent-06 体育尾盘",

            interval_seconds=30,

            min_interval=15,

            interval_setting_key="interval_sports_endgame"

        )

        self._scanned: set = set()



    async def scan_opportunities(self) -> List[Signal]:

        signals = []



        try:

            # Step 1: 获取实时比分（已锁定的比赛）

            live_games = await sports_live.get_live_scores()

            recent = await sports_live.get_recent_results()

            all_games = live_games + recent



            locked = [g for g in all_games if g.get('is_locked')]



            if not locked:

                live_count = len([g for g in all_games if g.get('is_live')])

                if all_games:

                    db.add_activity(self.name, "监控",

                        f"{len(all_games)}场比赛 ({live_count}进行中) 0锁定", "👀")

                else:

                    db.add_activity(self.name, "扫描", "当前无进行中的大赛", "⏳")

                return signals



            db.add_activity(self.name, "锁定",

                f"🔒 {len(locked)} 场比赛结果已锁定！", "🔒")



            # Step 2: 获取体育市场（只要单场比赛）

            sports_markets = await self._get_single_game_markets()



            if not sports_markets:

                db.add_activity(self.name, "无市场",

                    "无匹配的单场比赛市场", "⏳")

                return signals



            db.add_activity(self.name, "市场",

                f"{len(sports_markets)} 个单场比赛市场", "🏟️")



            # Step 3: 匹配锁定比赛 → 市场

            for game in locked:

                for market in sports_markets:

                    signal = self._match_and_signal(game, market)

                    if signal:

                        signals.append(signal)



        except Exception as e:

            logger.error(f"体育尾盘异常: {e}", exc_info=True)



        return signals



    async def _get_single_game_markets(self) -> List[Dict]:

        """只获取单场比赛市场，排除赛季冠军"""

        all_sports = await polymarket_client.get_sports_markets(limit=100)



        single_game = []

        now = datetime.utcnow()



        for m in all_sports:

            q = m.get('question', '').lower()



            # 排除赛季/锦标赛市场

            if any(bw in q for bw in SEASON_BLACKLIST):

                continue



            # 检查截止日期：单场比赛一般在7天内结算

            end_str = (m.get('endDate') or m.get('end_date_iso') or '')

            if end_str:

                try:

                    end_dt = datetime.fromisoformat(

                        str(end_str).replace('Z', '+00:00')

                    ).replace(tzinfo=None)

                    days_left = (end_dt - now).days

                    if days_left > 7:  # 超过7天 = 不是单场比赛

                        continue

                except:

                    pass



            single_game.append(m)



        return single_game



    def _match_and_signal(self, game: Dict, market: Dict) -> Optional[Signal]:

        """匹配锁定比赛到市场并生成信号"""

        mid = market.get('id', market.get('condition_id', ''))

        cache_key = f"{mid}_{game.get('event_id', '')}"



        if cache_key in self._scanned:

            return None



        q = market.get('question', '').lower()

        winning = game.get('winning_team', '').lower()

        losing = game.get('losing_team', '').lower()

        home = game.get('home_team', '').lower()

        away = game.get('away_team', '').lower()



        # 检查市场是否包含这场比赛的球队

        all_teams = [winning, losing, home, away]

        team_words = set()

        for team in all_teams:

            for word in team.split():

                if len(word) > 2:

                    team_words.add(word.lower())



        match_count = sum(1 for w in team_words if w in q)

        if match_count < 1:

            return None



        # 判断买哪边

        # 如果问题包含赢家名字 → 买YES

        winner_in_q = any(w in q for w in winning.split() if len(w) > 2)



        if winner_in_q:

            price = polymarket_client._extract_yes_price(market)

            if price is None:

                return None

            direction = "BUY_YES"

        else:

            # 问题包含输家名字 → 买NO

            loser_in_q = any(w in q for w in losing.split() if len(w) > 2)

            if loser_in_q:

                price = polymarket_client.extract_no_price(market)

                if price is None:

                    return None

                direction = "BUY_NO"

            else:

                return None



        # 价格检查：0.92-0.98 才是甜蜜点

        if price < 0.92 or price > 0.99:

            return None



        edge = 1.0 - price

        if edge < 0.01:

            return None



        self._scanned.add(cache_key)

        if len(self._scanned) > 300:

            self._scanned.clear()



        confidence = game.get('lock_confidence', 0.99)

        score = game.get('score_display', '?-?')

        reason = game.get('lock_reason', '')

        league = game.get('league', '')



        reasoning = (

            f"🏆 {league} 尾盘锁定: "

            f"{game.get('home_team','')} vs {game.get('away_team','')} "

            f"({score}) {reason} | "

            f"{direction} @{price:.2%}→100% (+{edge:.2%})"

        )



        logger.info(f"体育尾盘信号: {reasoning}")



        return Signal(

            agent_name=self.name, market_id=mid,

            market_title=market.get('question', ''),

            direction=direction, entry_price=price,

            fair_value=1.0, edge=edge, confidence=confidence, size=0,

            reasoning=reasoning,

            metadata={

                'strategy': 'endgame',

                'sport': game.get('sport', ''),

                'league': league,

                'score': score,

                'lock_reason': reason,

            }

        )


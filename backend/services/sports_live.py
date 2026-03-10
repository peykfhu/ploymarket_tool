
"""

体育实时比分服务

- 免费 API：api-football.com / thesportsdb.com

- 只关注大赛：NBA、英超、NFL、欧冠、西甲、德甲

"""

import aiohttp

import asyncio

from typing import Dict, List, Optional

from datetime import datetime

from config import config

from utils.logger import get_logger



logger = get_logger("sports_live")



# 只关注的大赛联赛ID（TheSportsDB免费API）

MAJOR_LEAGUES = {

    # NBA

    "NBA": {"league": "4387", "sport": "Basketball"},

    # 英超

    "English Premier League": {"league": "4328", "sport": "Soccer"},

    # 西甲

    "Spanish La Liga": {"league": "4335", "sport": "Soccer"},

    # 德甲

    "German Bundesliga": {"league": "4331", "sport": "Soccer"},

    # 欧冠

    "UEFA Champions League": {"league": "4480", "sport": "Soccer"},

    # NFL

    "NFL": {"league": "4391", "sport": "American Football"},

    # 意甲

    "Italian Serie A": {"league": "4332", "sport": "Soccer"},

}



# NBA/NFL 尾盘判定阈值

LOCKDOWN_RULES = {

    "Basketball": {

        "time_remaining_seconds": 120,    # 最后2分钟

        "min_lead": 15,                   # 领先15分

        "min_confidence": 0.99,

    },

    "Soccer": {

        "time_remaining_seconds": 0,      # 终场哨（FT）

        "min_lead": 1,                    # 领先1球

        "min_confidence": 0.995,          # 足球终场后99.5%确定

    },

    "American Football": {

        "time_remaining_seconds": 120,    # 最后2分钟

        "min_lead": 14,                   # 领先两个达阵

        "min_confidence": 0.98,

    },

}





class SportsLiveService:

    """实时比分 + 尾盘锁定检测"""



    def __init__(self):

        self.session: Optional[aiohttp.ClientSession] = None

        # TheSportsDB 免费 API（无需API Key，限50次/分钟）

        self.base_url = "https://www.thesportsdb.com/api/v1/json/3"



    async def _get_session(self) -> aiohttp.ClientSession:

        if self.session is None or self.session.closed:

            self.session = aiohttp.ClientSession(

                timeout=aiohttp.ClientTimeout(total=15)

            )

        return self.session



    async def get_live_scores(self) -> List[Dict]:

        """获取所有正在进行的比赛"""

        session = await self._get_session()

        try:

            # TheSportsDB 实时比分（免费）

            async with session.get(

                f"{self.base_url}/livescore.php"

            ) as resp:

                if resp.status == 200:

                    data = await resp.json()

                    events = data.get("events") or data.get("livescore") or []

                    if not events:

                        return []

                    return self._parse_events(events)

                return []

        except Exception as e:

            logger.error(f"获取实时比分异常: {e}")

            return []



    async def get_recent_results(self) -> List[Dict]:

        """获取最近完成的比赛（尾盘扫货重点）"""

        session = await self._get_session()

        results = []



        for league_name, info in MAJOR_LEAGUES.items():

            try:

                async with session.get(

                    f"{self.base_url}/eventspastleague.php",

                    params={"id": info["league"]}

                ) as resp:

                    if resp.status == 200:

                        data = await resp.json()

                        events = data.get("events") or []

                        for e in events[:5]:  # 最近5场

                            parsed = self._parse_single_event(e, info["sport"])

                            if parsed:

                                results.append(parsed)

                await asyncio.sleep(0.5)  # 限流

            except Exception as e:

                logger.error(f"获取{league_name}结果异常: {e}")



        return results



    async def get_today_events(self) -> List[Dict]:

        """获取今天的比赛"""

        session = await self._get_session()

        today = datetime.utcnow().strftime("%Y-%m-%d")

        try:

            async with session.get(

                f"{self.base_url}/eventsday.php",

                params={"d": today}

            ) as resp:

                if resp.status == 200:

                    data = await resp.json()

                    events = data.get("events") or []

                    return self._parse_events(events)

                return []

        except Exception as e:

            logger.error(f"获取今日比赛异常: {e}")

            return []



    def _parse_events(self, events: list) -> List[Dict]:

        """解析比赛列表"""

        parsed = []

        for e in events:

            p = self._parse_single_event(e)

            if p:

                parsed.append(p)

        return parsed



    def _parse_single_event(self, e: dict, sport_override: str = None) -> Optional[Dict]:

        """解析单场比赛"""

        try:

            league = e.get("strLeague", "")



            # 只关注大赛

            is_major = any(name.lower() in league.lower() for name in MAJOR_LEAGUES)

            if not is_major:

                return None



            sport = sport_override or e.get("strSport", "")

            home_team = e.get("strHomeTeam", "")

            away_team = e.get("strAwayTeam", "")

            home_score = self._safe_int(e.get("intHomeScore"))

            away_score = self._safe_int(e.get("intAwayScore"))

            status = e.get("strStatus", e.get("strProgress", ""))

            event_id = e.get("idEvent", "")



            if home_score is None or away_score is None:

                return None



            # 判断比赛状态

            is_finished = status.upper() in ["FT", "AET", "FT/PEN", "FINISHED",

                                               "FINAL", "F", "COMPLETED"]

            is_live = status.upper() in ["LIVE", "1H", "2H", "HT",

                                          "Q1", "Q2", "Q3", "Q4", "OT"]



            # 计算领先

            lead = abs(home_score - away_score)

            winning_team = home_team if home_score > away_score else away_team

            losing_team = away_team if home_score > away_score else home_team



            # 尾盘锁定检测

            lockdown = self._check_lockdown(sport, status, lead, is_finished)



            return {

                "event_id": event_id,

                "league": league,

                "sport": sport,

                "home_team": home_team,

                "away_team": away_team,

                "home_score": home_score,

                "away_score": away_score,

                "score_display": f"{home_score}-{away_score}",

                "status": status,

                "is_finished": is_finished,

                "is_live": is_live,

                "lead": lead,

                "winning_team": winning_team,

                "losing_team": losing_team,

                "is_locked": lockdown["locked"],

                "lock_confidence": lockdown["confidence"],

                "lock_reason": lockdown["reason"],

            }

        except Exception as e:

            logger.error(f"解析比赛异常: {e}")

            return None



    def _check_lockdown(self, sport: str, status: str,

                         lead: int, is_finished: bool) -> Dict:

        """检测比赛结果是否已锁定"""

        result = {"locked": False, "confidence": 0.0, "reason": ""}



        if is_finished and lead > 0:

            result["locked"] = True

            result["confidence"] = 0.999

            result["reason"] = f"比赛已结束 领先{lead}"

            return result



        rules = None

        for sport_type, r in LOCKDOWN_RULES.items():

            if sport_type.lower() in sport.lower():

                rules = r

                break



        if not rules:

            return result



        # 足球：终场哨 = 锁定

        if "soccer" in sport.lower() or "football" in sport.lower():

            if is_finished and lead >= rules["min_lead"]:

                result["locked"] = True

                result["confidence"] = rules["min_confidence"]

                result["reason"] = f"终场 {lead}-0领先"



        # 篮球/美式足球：大比分领先 + 末节

        elif "basketball" in sport.lower():

            if status.upper() in ["Q4", "OT"] and lead >= rules["min_lead"]:

                result["locked"] = True

                result["confidence"] = rules["min_confidence"]

                result["reason"] = f"Q4/OT 领先{lead}分"

            elif is_finished:

                result["locked"] = True

                result["confidence"] = 0.999

                result["reason"] = f"比赛结束"



        elif "american" in sport.lower():

            if status.upper() in ["Q4", "OT"] and lead >= rules["min_lead"]:

                result["locked"] = True

                result["confidence"] = rules["min_confidence"]

                result["reason"] = f"Q4 领先{lead}分"



        return result



    def _safe_int(self, val) -> Optional[int]:

        if val is None:

            return None

        try:

            return int(val)

        except (ValueError, TypeError):

            return None



    async def close(self):

        if self.session and not self.session.closed:

            await self.session.close()





sports_live = SportsLiveService()


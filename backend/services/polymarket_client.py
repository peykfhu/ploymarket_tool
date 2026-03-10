
"""

Polymarket 市场获取 - 修复版



关键修复：

1. 过滤已过期市场（end_date < 今天的不要）

2. 使用正确的 API 端点和参数

3. 气候科学用关键词精确匹配，不依赖可能错误的 tag_slug

4. 体育市场只获取当前赛季的

"""

import aiohttp

import hmac

import hashlib

import time

import json

from typing import Dict, List, Optional

from datetime import datetime, timedelta

from config import config

from utils.logger import get_logger
from services.market_classifier import classify_market, filter_by_category



logger = get_logger("polymarket_client")





class PolymarketClient:



    def __init__(self):

        self.clob_url = config.POLYMARKET_BASE_URL  # https://clob.polymarket.com

        self.gamma_url = "https://gamma-api.polymarket.com"

        self.api_key = config.POLYMARKET_API_KEY

        self.api_secret = config.POLYMARKET_API_SECRET

        self.passphrase = config.POLYMARKET_PASSPHRASE

        self.session: Optional[aiohttp.ClientSession] = None

        self.dry_run = config.DRY_RUN

        self._all_markets_cache: List[Dict] = []

        self._cache_ts: float = 0



    async def _get_session(self) -> aiohttp.ClientSession:

        if self.session is None or self.session.closed:

            headers = {"Content-Type": "application/json"}

            if self.api_key:

                headers["POLY_API_KEY"] = self.api_key

            if self.passphrase:

                headers["POLY_PASSPHRASE"] = self.passphrase

            self.session = aiohttp.ClientSession(

                headers=headers,

                timeout=aiohttp.ClientTimeout(total=30)

            )

        return self.session



    def _sign_request(self, method: str, path: str, body: str = "") -> Dict[str, str]:

        ts = str(int(time.time()))

        msg = f"{ts}{method}{path}{body}"

        sig = hmac.new(self.api_secret.encode(), msg.encode(),

                       hashlib.sha256).hexdigest() if self.api_secret else ""

        return {"POLY_TIMESTAMP": ts, "POLY_SIGNATURE": sig}



    # ==========================================

    # 核心：获取当前活跃市场（自动过滤过期）

    # ==========================================



    async def get_active_markets(self, limit: int = 200) -> List[Dict]:

        """

        获取当前活跃且未过期的市场

        这是所有 Agent 应该调用的主方法

        """

        now = time.time()

        # 缓存60秒

        if self._all_markets_cache and (now - self._cache_ts < 60):

            return self._all_markets_cache



        markets = []



        # 方法1: Gamma API（更全）

        gamma_markets = await self._fetch_gamma_markets(limit=limit)

        if gamma_markets:

            markets = gamma_markets



        # 方法2: CLOB API（备用）

        if not markets:

            clob_markets = await self._fetch_clob_markets(limit=limit)

            markets = clob_markets



        # 关键：过滤掉已过期的市场

        active = self._filter_active(markets)



        logger.info(f"获取到 {len(markets)} 个市场，过滤后 {len(active)} 个活跃")



        self._all_markets_cache = active

        self._cache_ts = now

        return active



    async def _fetch_gamma_markets(self, limit: int = 200) -> List[Dict]:

        """Gamma API 获取市场"""

        session = await self._get_session()

        all_markets = []



        try:

            # Gamma API 支持 offset 分页

            for offset in range(0, limit, 100):

                params = {

                    "limit": min(100, limit - offset),

                    "offset": offset,

                    "active": "true",

                    "closed": "false",

                }

                async with session.get(

                    f"{self.gamma_url}/markets", params=params

                ) as resp:

                    if resp.status == 200:

                        data = await resp.json()

                        batch = data if isinstance(data, list) else data.get('data', [])

                        if not batch:

                            break

                        all_markets.extend(batch)

                    else:

                        text = await resp.text()

                        logger.warning(f"Gamma API {resp.status}: {text[:100]}")

                        break

                await asyncio.sleep(0.3)



            return all_markets

        except Exception as e:

            logger.error(f"Gamma API 异常: {e}")

            return []



    async def _fetch_clob_markets(self, limit: int = 200) -> List[Dict]:

        """CLOB API 获取市场"""

        session = await self._get_session()

        try:

            params = {"limit": limit, "active": "true"}

            async with session.get(

                f"{self.clob_url}/markets", params=params

            ) as resp:

                if resp.status == 200:

                    data = await resp.json()

                    return data if isinstance(data, list) else data.get('data', data.get('markets', []))

                return []

        except Exception as e:

            logger.error(f"CLOB API 异常: {e}")

            return []



    def _filter_active(self, markets: List[Dict]) -> List[Dict]:

        """

        过滤掉已过期/已关闭的市场

        只保留：end_date > 今天 或 没有 end_date 的

        """

        now = datetime.utcnow()

        active = []



        for m in markets:

            # 检查是否已关闭

            if m.get('closed') == True or m.get('active') == False:

                continue



            # 检查结束日期

            end_date_str = (m.get('endDate') or m.get('end_date_iso')

                            or m.get('endDateIso') or m.get('close_time') or '')



            if end_date_str:

                try:

                    # 处理各种日期格式

                    end_str = str(end_date_str).replace('Z', '+00:00')

                    if 'T' in end_str:

                        end_dt = datetime.fromisoformat(end_str).replace(tzinfo=None)

                    else:

                        end_dt = datetime.strptime(end_str[:10], '%Y-%m-%d')



                    # 已过期：跳过

                    if end_dt < now - timedelta(days=1):

                        continue

                except (ValueError, TypeError):

                    pass  # 无法解析日期，保留



            # 检查是否有价格（没有价格的可能是无效市场）

            price = self._extract_yes_price(m)

            if price is not None and price <= 0:

                continue



            active.append(m)



        return active



    # ==========================================

    # 分类市场查询（基于关键词精确匹配）

    # ==========================================



    async def get_climate_markets(self, limit: int = 50) -> List[Dict]:

        """使用精确分类器获取气候市场"""

        all_markets = await self.get_active_markets(limit=500)

        result = filter_by_category(all_markets, 'climate')

        logger.info(f"气候市场: {len(all_markets)} → {len(result)}")

        return result[:limit]



    async def _get_climate_markets_old(self, limit: int = 50) -> List[Dict]:

        """

        获取气候/天气市场



        不依赖 tag_slug（可能不准确）

        直接用关键词从活跃市场中筛选

        """

        all_markets = await self.get_active_markets(limit=500)



        climate_keywords = [

            'temperature', 'rain', 'snow', 'weather', 'climate',

            'heat', 'cold', 'storm', 'hurricane', 'celsius',

            'fahrenheit', 'precipitation', 'flood', 'drought',

            'hottest', 'coldest', 'warmest', 'record high', 'record low',

            'heat wave', 'polar vortex', 'el nino', 'la nina',

            'global warming', 'carbon', 'emissions', 'arctic',

            'sea level', 'wildfire', 'tornado', 'typhoon',

            'degree', 'noaa', 'forecast',

        ]



        # 城市名也算天气相关

        from services.noaa_client import MAJOR_CITIES

        city_names = [c.lower() for c in MAJOR_CITIES.keys()]



        result = []

        for m in all_markets:

            q = m.get('question', '').lower()

            desc = (m.get('description', '') or '').lower()

            tags = ' '.join(m.get('tags', []) if isinstance(m.get('tags'), list) else []).lower()

            text = f"{q} {desc} {tags}"



            # 直接匹配气候关键词

            if any(kw in text for kw in climate_keywords):

                result.append(m)

                continue



            # 城市名 + 天气相关动词

            if any(city in text for city in city_names):

                if any(w in text for w in ['above', 'below', 'reach', 'exceed',

                                            'temperature', 'rain', 'snow', 'hot', 'cold']):

                    result.append(m)



        logger.info(f"气候市场筛选: {len(all_markets)} → {len(result)}")

        return result[:limit]



    async def get_sports_markets(self, limit: int = 100) -> List[Dict]:

        """使用精确分类器获取体育市场"""

        all_markets = await self.get_active_markets(limit=500)

        result = filter_by_category(all_markets, 'sports')

        logger.info(f"体育市场: {len(all_markets)} → {len(result)}")

        return result[:limit]



    async def _get_sports_markets_old(self, limit: int = 100) -> List[Dict]:

        """获取体育市场（只要大赛）"""

        all_markets = await self.get_active_markets(limit=500)



        sports_keywords = [

            'nba', 'nfl', 'mlb', 'nhl',

            'premier league', 'champions league', 'la liga',

            'bundesliga', 'serie a', 'world cup', 'euro',

            'lakers', 'celtics', 'warriors', 'knicks', 'nets',

            'bucks', 'heat', 'suns', 'mavericks', 'nuggets',

            'arsenal', 'manchester', 'liverpool', 'chelsea', 'tottenham',

            'real madrid', 'barcelona', 'bayern',

            'chiefs', 'eagles', '49ers', 'cowboys',

            'super bowl', 'playoff', 'finals', 'championship',

            'mvp', 'win the', 'win game', 'beat',

        ]



        result = []

        for m in all_markets:

            q = m.get('question', '').lower()

            desc = (m.get('description', '') or '').lower()

            text = f"{q} {desc}"



            if any(kw in text for kw in sports_keywords):

                result.append(m)



        logger.info(f"体育市场筛选: {len(all_markets)} → {len(result)}")

        return result[:limit]



    async def get_crypto_markets(self, limit: int = 50) -> List[Dict]:

        """使用精确分类器获取加密市场"""

        all_markets = await self.get_active_markets(limit=500)

        result = filter_by_category(all_markets, 'crypto')

        logger.info(f"加密市场: {len(all_markets)} → {len(result)}")

        return result[:limit]



    async def _get_crypto_markets_old(self, limit: int = 50) -> List[Dict]:

        """获取加密货币市场"""

        all_markets = await self.get_active_markets(limit=500)



        crypto_keywords = [

            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto',

            'solana', 'sol', 'dogecoin', 'doge', 'xrp',

            'blockchain', 'defi', 'nft', 'token',

            'bitcoin price', 'btc price', 'crypto market',

            'bitcoin above', 'bitcoin below', 'bitcoin reach',

        ]



        result = []

        for m in all_markets:

            q = m.get('question', '').lower()

            if any(kw in q for kw in crypto_keywords):

                result.append(m)



        return result[:limit]



    async def get_politics_markets(self, limit: int = 50) -> List[Dict]:

        """获取政治市场"""

        all_markets = await self.get_active_markets(limit=500)



        keywords = [

            'election', 'president', 'senate', 'congress', 'vote',

            'democrat', 'republican', 'trump', 'biden', 'harris',

            'governor', 'primary', 'nomination', 'political',

            'poll', 'approval', 'impeach',

        ]



        result = []

        for m in all_markets:

            q = m.get('question', '').lower()

            if any(kw in q for kw in keywords):

                result.append(m)



        return result[:limit]



    # ==========================================

    # 价格提取（兼容多种 API 格式）

    # ==========================================



    def _extract_yes_price(self, market: Dict) -> Optional[float]:

        """从市场数据提取 YES 价格"""

        try:

            # 格式1: tokens 数组

            if 'tokens' in market and isinstance(market['tokens'], list):

                for t in market['tokens']:

                    if t.get('outcome') == 'Yes':

                        p = t.get('price')

                        if p is not None:

                            return float(p)



            # 格式2: outcomePrices

            op = market.get('outcomePrices')

            if op:

                if isinstance(op, str):

                    try:

                        op = json.loads(op)

                    except:

                        pass

                if isinstance(op, list) and len(op) > 0:

                    return float(op[0])



            # 格式3: bestAsk / bestBid

            if 'bestAsk' in market:

                return float(market['bestAsk'])

            if 'bestBid' in market:

                return float(market['bestBid'])



            return None

        except (ValueError, TypeError, IndexError):

            return None



    def extract_no_price(self, market: Dict) -> Optional[float]:

        """提取 NO 价格"""

        try:

            if 'tokens' in market and isinstance(market['tokens'], list):

                for t in market['tokens']:

                    if t.get('outcome') == 'No':

                        p = t.get('price')

                        if p is not None:

                            return float(p)



            op = market.get('outcomePrices')

            if op:

                if isinstance(op, str):

                    try:

                        op = json.loads(op)

                    except:

                        pass

                if isinstance(op, list) and len(op) > 1:

                    return float(op[1])



            return None

        except (ValueError, TypeError, IndexError):

            return None



    # ==========================================

    # 交易相关

    # ==========================================



    async def get_orderbook(self, token_id: str) -> Dict:

        session = await self._get_session()

        try:

            async with session.get(f"{self.clob_url}/book",

                                   params={"token_id": token_id}) as resp:

                if resp.status == 200:

                    return await resp.json()

                return {"bids": [], "asks": []}

        except Exception as e:

            logger.error(f"订单簿异常: {e}")

            return {"bids": [], "asks": []}



    async def get_price(self, token_id: str) -> Optional[float]:

        book = await self.get_orderbook(token_id)

        bids = book.get("bids", [])

        if bids:

            return float(bids[0]["price"])

        return None



    async def place_order(self, token_id: str, side: str,

                          price: float, size: float) -> Optional[Dict]:

        if self.dry_run:

            return {

                "id": f"dry_{int(time.time()*1000)}",

                "token_id": token_id, "side": side,

                "price": price, "size": size,

                "status": "simulated", "dry_run": True

            }



        session = await self._get_session()

        path = "/order"

        body = json.dumps({

            "tokenID": token_id, "side": side.upper(),

            "price": str(price), "size": str(size), "type": "GTC"

        })

        headers = self._sign_request("POST", path, body)

        try:

            async with session.post(f"{self.clob_url}{path}",

                                    data=body, headers=headers) as resp:

                if resp.status in (200, 201):

                    return await resp.json()

                text = await resp.text()

                logger.error(f"下单失败: {resp.status} {text[:200]}")

                return None

        except Exception as e:

            logger.error(f"下单异常: {e}")

            return None



    async def get_balance(self) -> Optional[float]:

        if self.dry_run:

            return None

        session = await self._get_session()

        path = "/balance"

        headers = self._sign_request("GET", path)

        try:

            async with session.get(f"{self.clob_url}{path}",

                                   headers=headers) as resp:

                if resp.status == 200:

                    data = await resp.json()

                    return float(data.get("balance", data.get("available", 0)))

                return None

        except:

            return None



    async def close(self):

        if self.session and not self.session.closed:

            await self.session.close()





import asyncio

polymarket_client = PolymarketClient()


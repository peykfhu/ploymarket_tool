# backend/services/polymarket_client.py
import aiohttp
import asyncio
import hmac
import hashlib
import time
import json
from typing import Dict, List, Optional
from config import config
from utils.logger import get_logger

logger = get_logger("polymarket_client")


class PolymarketClient:
    """
    Polymarket CLOB API 客户端
    文档: https://docs.polymarket.com/
    """

    def __init__(self):
        self.base_url = config.POLYMARKET_BASE_URL
        self.api_key = config.POLYMARKET_API_KEY
        self.api_secret = config.POLYMARKET_API_SECRET
        self.session: Optional[aiohttp.ClientSession] = None
        self.dry_run = config.DRY_RUN

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json",
                    "POLY_API_KEY": self.api_key,
                },
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session

    def _sign_request(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        timestamp = str(int(time.time()))
        message = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return {
            "POLY_TIMESTAMP": timestamp,
            "POLY_SIGNATURE": signature,
        }

    async def get_markets(self, limit: int = 100,
                          active: bool = True,
                          category: str = None) -> List[Dict]:
        """获取所有活跃市场"""
        session = await self._get_session()
        params = {"limit": limit, "active": active}
        if category:
            params["tag"] = category

        try:
            async with session.get(
                f"{self.base_url}/markets",
                params=params
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data if isinstance(data, list) else data.get('data', [])
                else:
                    logger.error(f"获取市场失败: {resp.status}")
                    return []
        except Exception as e:
            logger.error(f"获取市场异常: {e}")
            return []

    async def get_market(self, market_id: str) -> Optional[Dict]:
        """获取单个市场详情"""
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.base_url}/markets/{market_id}"
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except Exception as e:
            logger.error(f"获取市场详情异常: {e}")
            return None

    async def get_orderbook(self, token_id: str) -> Dict:
        """获取订单簿"""
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.base_url}/book",
                params={"token_id": token_id}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {"bids": [], "asks": []}
        except Exception as e:
            logger.error(f"获取订单簿异常: {e}")
            return {"bids": [], "asks": []}

    async def get_price(self, token_id: str) -> Optional[float]:
        """获取当前最优价格"""
        book = await self.get_orderbook(token_id)
        if book.get("bids"):
            return float(book["bids"][0]["price"])
        return None

    async def place_order(self, token_id: str, side: str,
                          price: float, size: float) -> Optional[Dict]:
        """下单"""
        if self.dry_run:
            order = {
                "id": f"dry_run_{int(time.time()*1000)}",
                "token_id": token_id,
                "side": side,
                "price": price,
                "size": size,
                "status": "simulated",
                "dry_run": True
            }
            logger.info(f"[DRY RUN] 模拟下单: {side} {size}@{price} on {token_id}")
            return order

        session = await self._get_session()
        path = "/order"
        body = json.dumps({
            "tokenID": token_id,
            "side": side.upper(),
            "price": str(price),
            "size": str(size),
            "type": "GTC"
        })

        headers = self._sign_request("POST", path, body)

        try:
            async with session.post(
                f"{self.base_url}{path}",
                data=body,
                headers=headers
            ) as resp:
                if resp.status in (200, 201):
                    result = await resp.json()
                    logger.info(f"下单成功: {result}")
                    return result
                else:
                    error_text = await resp.text()
                    logger.error(f"下单失败: {resp.status} - {error_text}")
                    return None
        except Exception as e:
            logger.error(f"下单异常: {e}")
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        if self.dry_run:
            logger.info(f"[DRY RUN] 模拟取消订单: {order_id}")
            return True

        session = await self._get_session()
        path = f"/order/{order_id}"
        headers = self._sign_request("DELETE", path)

        try:
            async with session.delete(
                f"{self.base_url}{path}",
                headers=headers
            ) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"取消��单异常: {e}")
            return False

    async def get_positions(self) -> List[Dict]:
        """获取当前持仓"""
        if self.dry_run:
            return []

        session = await self._get_session()
        path = "/positions"
        headers = self._sign_request("GET", path)

        try:
            async with session.get(
                f"{self.base_url}{path}",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return []
        except Exception as e:
            logger.error(f"获取持仓异常: {e}")
            return []

    async def search_markets(self, query: str) -> List[Dict]:
        """搜索市场"""
        markets = await self.get_markets(limit=200)
        query_lower = query.lower()
        return [m for m in markets if query_lower in m.get('question', '').lower()]

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


polymarket_client = PolymarketClient()
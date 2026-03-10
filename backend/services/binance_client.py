from typing import Dict, List, Optional
from typing import Dict, List, Optional
# backend/services/binance_client.py
import aiohttp
import asyncio
import hmac
import hashlib
import time
from typing import Dict, List, Optional
from config import config
from utils.logger import get_logger

logger = get_logger("binance_client")


class BinanceClient:
    """Binance API 客户端 - 获取实时加密货币价格"""

    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.api_key = config.BINANCE_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        self._price_cache: Dict[str, Dict] = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"X-MBX-APIKEY": self.api_key},
                timeout=aiohttp.ClientTimeout(total=15)
            )
        return self.session

    async def get_btc_price(self) -> Optional[float]:
        """获取 BTC/USDT 实时价格"""
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.base_url}/api/v3/ticker/price",
                params={"symbol": "BTCUSDT"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    price = float(data["price"])
                    self._price_cache["BTCUSDT"] = {
                        "price": price,
                        "timestamp": time.time()
                    }
                    return price
                return None
        except Exception as e:
            logger.error(f"获取BTC价格异常: {e}")
            return None

    async def get_eth_price(self) -> Optional[float]:
        """获取 ETH/USDT 实时价格"""
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.base_url}/api/v3/ticker/price",
                params={"symbol": "ETHUSDT"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return float(data["price"])
                return None
        except Exception as e:
            logger.error(f"获取ETH价格异常: {e}")
            return None

    async def get_24h_stats(self, symbol: str = "BTCUSDT") -> Optional[Dict]:
        """获取24小时统计"""
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.base_url}/api/v3/ticker/24hr",
                params={"symbol": symbol}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "price": float(data["lastPrice"]),
                        "high": float(data["highPrice"]),
                        "low": float(data["lowPrice"]),
                        "volume": float(data["volume"]),
                        "change_percent": float(data["priceChangePercent"]),
                    }
                return None
        except Exception as e:
            logger.error(f"获取24h统计异常: {e}")
            return None

    async def get_klines(self, symbol: str = "BTCUSDT",
                         interval: str = "1h", limit: int = 24) -> list:
        """获取K线数据"""
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.base_url}/api/v3/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "limit": limit
                }
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [{
                        "open_time": k[0],
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                    } for k in data]
                return []
        except Exception as e:
            logger.error(f"获取K线异常: {e}")
            return []

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


binance_client = BinanceClient()
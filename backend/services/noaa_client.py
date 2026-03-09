# backend/services/noaa_client.py
import aiohttp
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from config import config
from utils.logger import get_logger

logger = get_logger("noaa_client")

# 主要城市坐标
MAJOR_CITIES = {
    "New York": (40.7128, -74.0060),
    "Los Angeles": (34.0522, -118.2437),
    "Chicago": (41.8781, -87.6298),
    "Houston": (29.7604, -95.3698),
    "Phoenix": (33.4484, -112.0740),
    "Philadelphia": (39.9526, -75.1652),
    "San Antonio": (29.4241, -98.4936),
    "San Diego": (32.7157, -117.1611),
    "Dallas": (32.7767, -96.7970),
    "Miami": (25.7617, -80.1918),
    "Atlanta": (33.7490, -84.3880),
    "Boston": (42.3601, -71.0589),
    "Seattle": (47.6062, -122.3321),
    "Denver": (39.7392, -104.9903),
    "Washington DC": (38.9072, -77.0369),
}


class NOAAClient:
    """NOAA 国家气象局 API 客户端"""

    def __init__(self):
        self.base_url = config.NOAA_BASE_URL
        self.token = config.NOAA_API_TOKEN
        self.session: Optional[aiohttp.ClientSession] = None
        self._grid_cache: Dict[str, Dict] = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            headers = {
                "User-Agent": "PolymarketBot/1.0 (contact@example.com)",
                "Accept": "application/geo+json",
            }
            if self.token:
                headers["token"] = self.token
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session

    async def get_grid_point(self, lat: float, lon: float) -> Optional[Dict]:
        """获取网格点信息（用于后续预报查询）"""
        cache_key = f"{lat},{lon}"
        if cache_key in self._grid_cache:
            return self._grid_cache[cache_key]

        session = await self._get_session()
        try:
            async with session.get(
                f"{self.base_url}/points/{lat},{lon}"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    grid_data = data.get("properties", {})
                    self._grid_cache[cache_key] = grid_data
                    return grid_data
                else:
                    logger.error(f"获取网格点失败: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"获取网格点异常: {e}")
            return None

    async def get_forecast(self, lat: float, lon: float) -> Optional[Dict]:
        """获取天气预报"""
        grid = await self.get_grid_point(lat, lon)
        if not grid:
            return None

        forecast_url = grid.get("forecast")
        if not forecast_url:
            return None

        session = await self._get_session()
        try:
            async with session.get(forecast_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("properties", {})
                return None
        except Exception as e:
            logger.error(f"获取预报异常: {e}")
            return None

    async def get_hourly_forecast(self, lat: float, lon: float) -> Optional[List[Dict]]:
        """获取逐小时预报"""
        grid = await self.get_grid_point(lat, lon)
        if not grid:
            return None

        forecast_url = grid.get("forecastHourly")
        if not forecast_url:
            return None

        session = await self._get_session()
        try:
            async with session.get(forecast_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    periods = data.get("properties", {}).get("periods", [])
                    return periods
                return None
        except Exception as e:
            logger.error(f"获取逐小时预报异常: {e}")
            return None

    async def get_precipitation_probability(
        self, city: str, hours_ahead: int = 24
    ) -> Optional[Dict]:
        """获取降水概率"""
        if city not in MAJOR_CITIES:
            logger.warning(f"未知城市: {city}")
            return None

        lat, lon = MAJOR_CITIES[city]
        hourly = await self.get_hourly_forecast(lat, lon)

        if not hourly:
            return None

        # 分析未来N小时的降水概率
        target_time = datetime.utcnow() + timedelta(hours=hours_ahead)
        rain_probs = []

        for period in hourly[:hours_ahead]:
            prob = period.get("probabilityOfPrecipitation", {})
            value = prob.get("value", 0) if prob else 0
            rain_probs.append({
                "time": period.get("startTime"),
                "probability": value or 0,
                "temperature": period.get("temperature"),
                "short_forecast": period.get("shortForecast", ""),
                "wind_speed": period.get("windSpeed", ""),
            })

        if not rain_probs:
            return None

        max_prob = max(p["probability"] for p in rain_probs)
        avg_prob = sum(p["probability"] for p in rain_probs) / len(rain_probs)
        any_rain = any("rain" in p["short_forecast"].lower() or
                       "storm" in p["short_forecast"].lower() or
                       "shower" in p["short_forecast"].lower()
                       for p in rain_probs)

        return {
            "city": city,
            "max_probability": max_prob,
            "avg_probability": avg_prob,
            "any_rain_forecast": any_rain,
            "hours_analyzed": len(rain_probs),
            "periods": rain_probs,
            "noaa_confidence": "high" if max_prob > 80 else "medium" if max_prob > 50 else "low"
        }

    async def scan_all_cities(self) -> List[Dict]:
        """扫描所有主要城市的天气数据"""
        results = []
        tasks = []

        for city in MAJOR_CITIES:
            tasks.append(self.get_precipitation_probability(city))

        city_results = await asyncio.gather(*tasks, return_exceptions=True)

        for city, result in zip(MAJOR_CITIES.keys(), city_results):
            if isinstance(result, Exception):
                logger.error(f"扫描 {city} 异常: {result}")
                continue
            if result:
                results.append(result)

        return results

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


noaa_client = NOAAClient()
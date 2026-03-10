
import aiohttp

import asyncio

from typing import Dict, List, Optional

from datetime import datetime, timedelta

from config import config

from utils.logger import get_logger



logger = get_logger("noaa_client")



MAJOR_CITIES = {

    "New York": (40.7128, -74.0060),

    "Los Angeles": (34.0522, -118.2437),

    "Chicago": (41.8781, -87.6298),

    "Houston": (29.7604, -95.3698),

    "Phoenix": (33.4484, -112.0740),

    "Philadelphia": (39.9526, -75.1652),

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

    def __init__(self):

        self.base_url = config.NOAA_BASE_URL

        self.token = config.NOAA_API_TOKEN

        self.session: Optional[aiohttp.ClientSession] = None

        self._grid_cache: Dict[str, Dict] = {}



    async def _get_session(self) -> aiohttp.ClientSession:

        if self.session is None or self.session.closed:

            headers = {

                "User-Agent": "PolymarketBot/1.0",

                "Accept": "application/geo+json",

            }

            if self.token:

                headers["token"] = self.token

            self.session = aiohttp.ClientSession(

                headers=headers, timeout=aiohttp.ClientTimeout(total=30)

            )

        return self.session



    async def get_grid_point(self, lat: float, lon: float) -> Optional[Dict]:

        cache_key = f"{lat},{lon}"

        if cache_key in self._grid_cache:

            return self._grid_cache[cache_key]

        session = await self._get_session()

        try:

            async with session.get(f"{self.base_url}/points/{lat},{lon}") as resp:

                if resp.status == 200:

                    data = await resp.json()

                    grid_data = data.get("properties", {})

                    self._grid_cache[cache_key] = grid_data

                    return grid_data

                return None

        except Exception as e:

            logger.error(f"获取网格点异常: {e}")

            return None



    async def get_hourly_forecast(self, lat: float, lon: float) -> Optional[List[Dict]]:

        grid = await self.get_grid_point(lat, lon)

        if not grid:

            return None

        url = grid.get("forecastHourly")

        if not url:

            return None

        session = await self._get_session()

        try:

            async with session.get(url) as resp:

                if resp.status == 200:

                    data = await resp.json()

                    return data.get("properties", {}).get("periods", [])

                return None

        except Exception as e:

            logger.error(f"获取逐小时预报异常: {e}")

            return None



    async def get_precipitation_probability(self, city: str, hours_ahead: int = 24) -> Optional[Dict]:

        if city not in MAJOR_CITIES:

            return None

        lat, lon = MAJOR_CITIES[city]

        hourly = await self.get_hourly_forecast(lat, lon)

        if not hourly:

            return None



        rain_probs = []

        for period in hourly[:hours_ahead]:

            prob = period.get("probabilityOfPrecipitation", {})

            value = prob.get("value", 0) if prob else 0

            rain_probs.append({

                "time": period.get("startTime"),

                "probability": value or 0,

                "short_forecast": period.get("shortForecast", ""),

            })



        if not rain_probs:

            return None



        max_prob = max(p["probability"] for p in rain_probs)

        avg_prob = sum(p["probability"] for p in rain_probs) / len(rain_probs)



        return {

            "city": city,

            "max_probability": max_prob,

            "avg_probability": avg_prob,

            "hours_analyzed": len(rain_probs),

            "noaa_confidence": "high" if max_prob > 80 else "medium" if max_prob > 50 else "low"

        }



    async def scan_all_cities(self) -> List[Dict]:

        results = []

        tasks = [self.get_precipitation_probability(city) for city in MAJOR_CITIES]

        city_results = await asyncio.gather(*tasks, return_exceptions=True)

        for city, result in zip(MAJOR_CITIES.keys(), city_results):

            if isinstance(result, Exception):

                continue

            if result:

                results.append(result)

        return results



    async def close(self):

        if self.session and not self.session.closed:

            await self.session.close()





noaa_client = NOAAClient()


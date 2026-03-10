
"""

市场分类器 — 精确分类，不再混乱

"""

from typing import List, Dict





# 各分类的精确关键词（互不重叠）

CLIMATE_KEYWORDS = [

    'temperature', 'rain', 'snow', 'weather', 'climate',

    'heat wave', 'cold snap', 'storm', 'hurricane', 'tornado',

    'celsius', 'fahrenheit', 'precipitation', 'flood', 'drought',

    'hottest', 'coldest', 'warmest', 'record high', 'record low',

    'wildfire', 'el nino', 'la nina', 'global warming',

    'carbon', 'emissions', 'arctic', 'sea level',

    'noaa', 'forecast', 'typhoon', 'blizzard',

]



SPORTS_KEYWORDS = [

    'nba', 'nfl', 'mlb', 'nhl', 'mls',

    'premier league', 'champions league', 'la liga',

    'bundesliga', 'serie a', 'ligue 1',

    'world cup', 'euro 202', 'copa america',

    'lakers', 'celtics', 'warriors', 'knicks', 'nets', 'bucks',

    'heat', 'suns', 'mavericks', 'nuggets', 'kings', 'bulls',

    'sixers', 'cavaliers', 'thunder', 'grizzlies', 'rockets',

    'arsenal', 'manchester city', 'man city', 'manchester united',

    'liverpool', 'chelsea', 'tottenham', 'newcastle',

    'real madrid', 'barcelona', 'bayern munich', 'dortmund',

    'juventus', 'inter milan', 'ac milan', 'napoli', 'psg',

    'chiefs', 'eagles', '49ers', 'cowboys', 'bills', 'ravens',

    'stanley cup', 'super bowl', 'playoff', 'finals',

    'championship', 'mvp', 'win game', 'beat',

    'tennis', 'golf', 'masters tournament', 'grand slam',

    'boxing', 'ufc', 'mma', 'fight',

]



CRYPTO_KEYWORDS = [

    'bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'sol',

    'dogecoin', 'doge', 'xrp', 'cardano', 'ada',

    'crypto', 'blockchain', 'defi', 'nft', 'token',

    'binance', 'coinbase', 'stablecoin', 'usdt', 'usdc',

    'altcoin', 'memecoin', 'web3', 'dao',

    'bitcoin price', 'btc price', 'crypto market',

    'halving', 'mining', 'wallet',

    'megaeth', 'gta vi',  # 这种虽然提到GTA但本质是crypto问题

]



POLITICS_KEYWORDS = [

    'election', 'president', 'senate', 'congress', 'vote',

    'democrat', 'republican', 'trump', 'biden', 'harris',

    'governor', 'primary', 'nomination', 'political',

    'poll', 'approval', 'impeach', 'cabinet', 'supreme court',

    'parliament', 'prime minister', 'legislation', 'bill',

]





def classify_market(market: Dict) -> str:

    """精确分类市场"""

    q = market.get('question', '').lower()

    desc = (market.get('description', '') or '').lower()

    text = f"{q} {desc}"



    # 优先级：体育 > 加密 > 政治 > 气候 > 其他

    # 因为体育关键词最具体



    sports_score = sum(1 for kw in SPORTS_KEYWORDS if kw in text)

    crypto_score = sum(1 for kw in CRYPTO_KEYWORDS if kw in text)

    politics_score = sum(1 for kw in POLITICS_KEYWORDS if kw in text)

    climate_score = sum(1 for kw in CLIMATE_KEYWORDS if kw in text)



    scores = {

        'sports': sports_score,

        'crypto': crypto_score,

        'politics': politics_score,

        'climate': climate_score,

    }



    best = max(scores, key=scores.get)

    if scores[best] == 0:

        return 'other'



    return best





def filter_by_category(markets: List[Dict], category: str) -> List[Dict]:

    """按分类过滤市场"""

    return [m for m in markets if classify_market(m) == category]



import asyncio

import json

import os

from datetime import datetime

from typing import Dict, Set



import uvicorn

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException

from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager



from config import config

from database import db

from agents.weather_agent import WeatherAgent

from agents.crypto_agent import CryptoAgent

from agents.politics_agent import PoliticsAgent

from agents.sports_agent import SportsAgent

from agents.endgame_agent import EndgameAgent

from agents.sports_endgame_agent import SportsEndgameAgent

from services.polymarket_client import polymarket_client

from services.notifier import notifier

from utils.logger import get_logger



os.makedirs("logs", exist_ok=True)

logger = get_logger("main")



agents: Dict[str, object] = {}

ws_clients: Set[WebSocket] = set()

scanned_markets_cache: Dict[str, list] = {}





def create_agents():

    global agents

    agents = {

        "weather": WeatherAgent(),

        "crypto": CryptoAgent(),

        "politics": PoliticsAgent(),

        "sports": SportsAgent(),

        "endgame": EndgameAgent(),

        "sports_endgame": SportsEndgameAgent(),

    }





@asynccontextmanager

async def lifespan(app: FastAPI):

    logger.info("🚀 Polymarket v4.1 启动 (6-Agent)")

    create_agents()

    for n, a in agents.items():

        await a.start()

    bt = asyncio.create_task(ws_broadcast_loop())

    mt = asyncio.create_task(market_scan_loop())

    yield

    for n, a in agents.items():

        await a.stop()

    bt.cancel()

    mt.cancel()





app = FastAPI(title="Polymarket套利系统", version="4.1.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,

                   allow_methods=["*"], allow_headers=["*"])





async def market_scan_loop():

    """定期扫描市场供前端展示（已修复：过滤过期）"""

    global scanned_markets_cache

    while True:

        try:

            climate = await polymarket_client.get_climate_markets(30)

            sports = await polymarket_client.get_sports_markets(30)

            crypto = await polymarket_client.get_crypto_markets(30)



            scanned_markets_cache = {

                "climate": [_simplify(m) for m in (climate or [])[:20]],

                "sports": [_simplify(m) for m in (sports or [])[:20]],

                "crypto": [_simplify(m) for m in (crypto or [])[:20]],

            }

            logger.info(f"市场扫描完成: 气候={len(climate or [])}, 体育={len(sports or [])}, 加密={len(crypto or [])}")

        except Exception as e:

            logger.error(f"市场扫描异常: {e}")

        await asyncio.sleep(120)





def _simplify(m: dict) -> dict:

    yes_price = polymarket_client._extract_yes_price(m)

    end = m.get('endDate', m.get('end_date_iso', ''))

    return {

        "id": m.get('id', m.get('condition_id', '')),

        "question": m.get('question', ''),

        "yes_price": yes_price,

        "volume": m.get('volume', m.get('volumeNum', 0)),

        "end_date": end,

    }





@app.get("/api/health")

async def health():

    return {"status": "running", "timestamp": datetime.utcnow().isoformat(),

            "dry_run": config.DRY_RUN, "agents_count": len(agents)}





@app.get("/api/dashboard")

async def get_dashboard():

    stats = db.get_all_stats()

    strat = db.get_strategy_stats()

    op = db.get_open_positions()

    tr = db.get_recent_trades(50)

    act = db.get_activities(40)

    ags = {n: a.get_state() for n, a in agents.items()}



    ini = db.get_setting('initial_balance', config.INITIAL_BALANCE)

    pnl = stats.get('total_pnl', 0) or 0



    rb = None

    if not config.DRY_RUN:

        rb = await polymarket_client.get_balance()



    bal = rb if rb is not None else (ini + pnl)



    return {

        "overview": {

            "initial_balance": ini, "current_balance": bal, "real_balance": rb,

            "total_pnl": pnl, "today_pnl": db.get_today_pnl(),

            "total_trades": stats.get('total_trades', 0) or 0,

            "win_rate": stats.get('win_rate', 0) or 0,

            "open_positions": len(op),

            "roi": (pnl / ini * 100) if ini > 0 else 0,

        },

        "strategy_stats": strat,

        "agents": ags,

        "recent_trades": tr[:20], "open_positions": op,

        "cumulative_pnl": db.get_cumulative_pnl(),

        "daily_pnl": db.get_daily_pnl(30),

        "activities": act, "dry_run": config.DRY_RUN,

    }





@app.get("/api/agents")

async def get_agents():

    return {n: a.get_state() for n, a in agents.items()}



@app.post("/api/agents/{name}/start")

async def start_agent(name: str):

    if name not in agents: raise HTTPException(404)

    await agents[name].start()

    return {"status": "started"}



@app.post("/api/agents/{name}/stop")

async def stop_agent(name: str):

    if name not in agents: raise HTTPException(404)

    await agents[name].stop()

    return {"status": "stopped"}



@app.get("/api/trades")

async def get_trades(limit: int = 100, status: str = None):

    if status == "open": return db.get_open_positions()

    return db.get_recent_trades(limit)



@app.get("/api/trades/stats")

async def get_trade_stats():

    return {"overall": db.get_all_stats(), "by_strategy": db.get_strategy_stats(),

            "by_agent": {n: db.get_agent_stats(a.name) for n, a in agents.items()}}



@app.get("/api/activities")

async def get_activities(limit: int = 50):

    return db.get_activities(limit)



@app.get("/api/markets/scanned")

async def get_scanned_markets(category: str = None):

    if category and category in scanned_markets_cache:

        return {"category": category, "markets": scanned_markets_cache.get(category, [])}

    return scanned_markets_cache



@app.get("/api/logs")

async def get_logs(agent_name: str = None, limit: int = 100):

    return db.get_agent_logs(agent_name, limit)



@app.get("/api/settings")

async def get_settings():

    saved = db.get_all_settings()

    defaults = {

        "max_position_size": config.MAX_POSITION_SIZE,

        "max_daily_loss": config.MAX_DAILY_LOSS,

        "min_edge": config.MIN_EDGE_THRESHOLD,

        "max_concurrent": config.MAX_CONCURRENT_POSITIONS,

        "stop_loss": config.STOP_LOSS_PERCENT,

        "daily_drawdown_limit": config.DAILY_DRAWDOWN_LIMIT,

        "initial_balance": config.INITIAL_BALANCE,

        "dry_run": config.DRY_RUN,

        "interval_weather": config.WEATHER_INTERVAL,

        "interval_crypto": config.CRYPTO_INTERVAL,

        "interval_politics": config.POLITICS_INTERVAL,

        "interval_sports": config.SPORTS_INTERVAL,

        "interval_endgame": config.ENDGAME_INTERVAL,

        "interval_sports_endgame": 30,

    }

    defaults.update(saved)

    return defaults



@app.post("/api/settings")

async def save_settings(settings: dict):

    for k, v in settings.items():

        db.save_setting(k, v)

    from services.risk_manager import risk_manager

    risk_manager.reload_settings()

    if 'dry_run' in settings:

        config.DRY_RUN = bool(settings['dry_run'])

        polymarket_client.dry_run = config.DRY_RUN

        db.add_activity("系统", "模式", f"→ {'模拟' if config.DRY_RUN else '🔴实盘'}", "⚡")

    return {"status": "saved"}



@app.get("/api/balance")

async def get_real_balance():

    b = await polymarket_client.get_balance()

    return {"real_balance": b, "dry_run": config.DRY_RUN}



@app.websocket("/ws")

async def ws_endpoint(ws: WebSocket):

    await ws.accept()

    ws_clients.add(ws)

    try:

        while True:

            data = await ws.receive_text()

            try:

                msg = json.loads(data)

                if msg.get('type') == 'ping': await ws.send_json({"type": "pong"})

            except: pass

    except WebSocketDisconnect:

        ws_clients.discard(ws)



async def ws_broadcast_loop():

    while True:

        try:

            if ws_clients:

                stats = db.get_all_stats()

                pnl = stats.get('total_pnl', 0) or 0

                ini = db.get_setting('initial_balance', config.INITIAL_BALANCE)

                data = {

                    "type": "update", "timestamp": datetime.utcnow().isoformat(),

                    "balance": ini + pnl, "total_pnl": pnl,

                    "today_pnl": db.get_today_pnl(),

                    "total_trades": stats.get('total_trades', 0) or 0,

                    "win_rate": stats.get('win_rate', 0) or 0,

                    "open_positions": len(db.get_open_positions()),

                    "dry_run": config.DRY_RUN,

                    "agents": {n: a.get_state() for n, a in agents.items()},

                    "recent_trades": db.get_recent_trades(5),

                    "activities": db.get_activities(15),

                }

                dead = set()

                for c in ws_clients:

                    try: await c.send_json(data)

                    except: dead.add(c)

                ws_clients -= dead

        except Exception as e:

            logger.error(f"WS: {e}")

        await asyncio.sleep(2)



if __name__ == "__main__":

    uvicorn.run("main:app", host="0.0.0.0", port=config.BACKEND_PORT, reload=False)






# ===== 新增：手动平仓 =====

@app.post("/api/trades/{trade_id}/close")

async def manual_close_trade(trade_id: int, body: dict = None):

    """手动止损/平仓"""

    positions = db.get_open_positions()

    target = None

    for p in positions:

        if p['id'] == trade_id:

            target = p

            break



    if not target:

        raise HTTPException(404, "未找到该持仓")



    # 获取当前价格

    current_price = None

    try:

        current_price = await polymarket_client.get_price(target['market_id'])

    except:

        pass



    if current_price is None:

        current_price = target['entry_price']  # fallback



    # 计算盈亏

    if target['direction'] in ('BUY_YES', 'BUY_NO'):

        pnl = (current_price - target['entry_price']) * target['size']

    else:

        pnl = (target['entry_price'] - current_price) * target['size']



    # 实盘下卖单

    if not config.DRY_RUN:

        await polymarket_client.place_order(

            token_id=target['market_id'],

            side="SELL" if "BUY" in target['direction'] else "BUY",

            price=current_price,

            size=target['size']

        )



    # 关闭交易

    db.close_trade(trade_id, current_price, pnl)



    emoji = "💰" if pnl > 0 else "💸"

    db.add_activity("手动操作", "平仓",

        f"#{trade_id} 手动平仓 PnL=${pnl:.2f}", emoji)



    return {

        "status": "closed",

        "trade_id": trade_id,

        "exit_price": current_price,

        "pnl": pnl

    }





# ===== 新增：持仓实时盈亏 =====

@app.get("/api/positions/live")

async def get_live_positions():

    """获取持仓 + 实时盈亏"""

    positions = db.get_open_positions()

    live = []



    for pos in positions:

        current_price = None

        try:

            current_price = await polymarket_client.get_price(pos['market_id'])

        except:

            pass



        if current_price is None:

            current_price = pos['entry_price']



        if pos['direction'] in ('BUY_YES', 'BUY_NO'):

            unrealized_pnl = (current_price - pos['entry_price']) * pos['size']

        else:

            unrealized_pnl = (pos['entry_price'] - current_price) * pos['size']



        pnl_pct = ((current_price - pos['entry_price']) / pos['entry_price'] * 100

                    if pos['entry_price'] > 0 else 0)



        live.append({

            **pos,

            'current_price': current_price,

            'unrealized_pnl': round(unrealized_pnl, 4),

            'pnl_percent': round(pnl_pct, 2),

        })



    return live


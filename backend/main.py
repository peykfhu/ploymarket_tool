# backend/main.py
import asyncio
import json
import os
import time
from datetime import datetime
from typing import Dict, Set

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from config import config
from database import db
from agents.weather_agent import WeatherAgent
from agents.crypto_agent import CryptoAgent
from agents.politics_agent import PoliticsAgent
from agents.sports_agent import SportsAgent
from services.notifier import notifier
from utils.logger import get_logger

# 确保日志目录存在
os.makedirs("logs", exist_ok=True)

logger = get_logger("main")

# 创建Agent实例
agents: Dict[str, object] = {}
ws_clients: Set[WebSocket] = set()


def create_agents():
    global agents
    agents = {
        "weather": WeatherAgent(),
        "crypto": CryptoAgent(),
        "politics": PoliticsAgent(),
        "sports": SportsAgent(),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 Polymarket套利系统启动中...")
    create_agents()

    # 启动所有agent
    for name, agent in agents.items():
        await agent.start()
        logger.info(f"✅ {agent.name} 已启动")

    # 启动WebSocket广播任务
    broadcast_task = asyncio.create_task(ws_broadcast_loop())

    # 启动每日报告
    report_task = asyncio.create_task(daily_report_loop())

    yield

    # 停止所有agent
    for name, agent in agents.items():
        await agent.stop()

    broadcast_task.cancel()
    report_task.cancel()
    logger.info("⏹ 系统已关闭")


app = FastAPI(
    title="Polymarket 套利系统",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()


def verify_password(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.password != config.DASHBOARD_PASSWORD:
        raise HTTPException(status_code=401, detail="密码错误")
    return credentials.username


# ==================== REST API ====================

@app.get("/api/health")
async def health_check():
    return {
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "dry_run": config.DRY_RUN,
        "agents_count": len(agents),
    }


@app.get("/api/dashboard")
async def get_dashboard():
    """获取仪表盘全部数据"""
    stats = db.get_all_stats()
    open_positions = db.get_open_positions()
    recent_trades = db.get_recent_trades(50)
    cumulative_pnl = db.get_cumulative_pnl()
    daily_pnl = db.get_daily_pnl(30)

    agent_states = {}
    for name, agent in agents.items():
        agent_states[name] = agent.get_state()

    initial_balance = 150
    total_pnl = stats.get('total_pnl', 0) or 0
    current_balance = initial_balance + total_pnl

    return {
        "overview": {
            "initial_balance": initial_balance,
            "current_balance": current_balance,
            "total_pnl": total_pnl,
            "total_trades": stats.get('total_trades', 0) or 0,
            "win_rate": stats.get('win_rate', 0) or 0,
            "open_positions": len(open_positions),
            "roi": (total_pnl / initial_balance * 100) if initial_balance > 0 else 0,
        },
        "agents": agent_states,
        "recent_trades": recent_trades[:20],
        "open_positions": open_positions,
        "cumulative_pnl": cumulative_pnl,
        "daily_pnl": daily_pnl,
    }


@app.get("/api/agents")
async def get_agents():
    """获取所有Agent状态"""
    result = {}
    for name, agent in agents.items():
        result[name] = agent.get_state()
    return result


@app.post("/api/agents/{agent_name}/start")
async def start_agent(agent_name: str):
    """启动指定Agent"""
    if agent_name not in agents:
        raise HTTPException(status_code=404, detail="Agent不存在")
    await agents[agent_name].start()
    return {"status": "started", "agent": agent_name}


@app.post("/api/agents/{agent_name}/stop")
async def stop_agent(agent_name: str):
    """停止指定Agent"""
    if agent_name not in agents:
        raise HTTPException(status_code=404, detail="Agent不存在")
    await agents[agent_name].stop()
    return {"status": "stopped", "agent": agent_name}


@app.get("/api/trades")
async def get_trades(limit: int = 100, status: str = None):
    """获取交易记录"""
    if status == "open":
        return db.get_open_positions()
    return db.get_recent_trades(limit)


@app.get("/api/trades/stats")
async def get_trade_stats():
    """获取交易统计"""
    return {
        "overall": db.get_all_stats(),
        "by_agent": {
            name: db.get_agent_stats(agent.name)
            for name, agent in agents.items()
        }
    }


@app.get("/api/pnl/daily")
async def get_daily_pnl(days: int = 30):
    return db.get_daily_pnl(days)


@app.get("/api/pnl/cumulative")
async def get_cumulative_pnl():
    return db.get_cumulative_pnl()


@app.get("/api/logs")
async def get_logs(agent_name: str = None, limit: int = 100):
    return db.get_agent_logs(agent_name, limit)


@app.post("/api/settings/risk")
async def update_risk_settings(settings: dict):
    """更新风控参数"""
    from services.risk_manager import risk_manager
    if 'max_position_size' in settings:
        risk_manager.max_position_size = settings['max_position_size']
    if 'max_daily_loss' in settings:
        risk_manager.max_daily_loss = settings['max_daily_loss']
    if 'min_edge' in settings:
        risk_manager.min_edge = settings['min_edge']
    if 'max_concurrent' in settings:
        risk_manager.max_concurrent = settings['max_concurrent']
    return {"status": "updated", "settings": settings}


# ==================== WebSocket ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.add(websocket)
    logger.info(f"WebSocket客户端连接, 当前{len(ws_clients)}个")

    try:
        while True:
            # 保持连接，接收客户端消息
            data = await websocket.receive_text()
            # 可以处理客户端发来的命令
            try:
                msg = json.loads(data)
                if msg.get('type') == 'ping':
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_clients.discard(websocket)
        logger.info(f"WebSocket客户端断开, 剩余{len(ws_clients)}个")


async def ws_broadcast_loop():
    """定时向所有WebSocket客户端广播数据"""
    while True:
        try:
            if ws_clients:
                stats = db.get_all_stats()
                open_positions = db.get_open_positions()
                recent_trades = db.get_recent_trades(10)
                recent_logs = db.get_agent_logs(limit=5)

                initial_balance = 150
                total_pnl = stats.get('total_pnl', 0) or 0

                data = {
                    "type": "update",
                    "timestamp": datetime.utcnow().isoformat(),
                    "balance": initial_balance + total_pnl,
                    "total_pnl": total_pnl,
                    "total_trades": stats.get('total_trades', 0) or 0,
                    "win_rate": stats.get('win_rate', 0) or 0,
                    "open_positions": len(open_positions),
                    "agents": {
                        name: agent.get_state()
                        for name, agent in agents.items()
                    },
                    "recent_trades": recent_trades[:5],
                    "recent_logs": recent_logs,
                }

                dead_clients = set()
                for client in ws_clients:
                    try:
                        await client.send_json(data)
                    except Exception:
                        dead_clients.add(client)

                ws_clients -= dead_clients

        except Exception as e:
            logger.error(f"WebSocket广播异常: {e}")

        await asyncio.sleep(3)  # 每3秒广播一次


async def daily_report_loop():
    """每日发送报告"""
    while True:
        await asyncio.sleep(86400)  # 24小时
        try:
            stats = db.get_all_stats()
            await notifier.send_daily_report(stats)
        except Exception as e:
            logger.error(f"发送每日报告异常: {e}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.BACKEND_PORT,
        reload=False,
        log_level="info"
    )
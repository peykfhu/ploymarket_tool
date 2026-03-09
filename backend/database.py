# backend/database.py
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from contextlib import contextmanager
import threading


class Database:
    _local = threading.local()

    def __init__(self, db_path: str = "polymarket_bot.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA busy_timeout=5000")
        return self._local.conn

    @contextmanager
    def get_cursor(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_db(self):
        with self.get_cursor() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT NOT NULL,
                    market_id TEXT NOT NULL,
                    market_title TEXT,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    size REAL NOT NULL,
                    profit_loss REAL DEFAULT 0,
                    status TEXT DEFAULT 'open',
                    edge REAL,
                    confidence REAL,
                    reasoning TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP,
                    metadata TEXT
                );

                CREATE TABLE IF NOT EXISTS agent_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_balance REAL NOT NULL,
                    available_balance REAL NOT NULL,
                    total_pnl REAL NOT NULL,
                    daily_pnl REAL NOT NULL,
                    open_positions INTEGER NOT NULL,
                    win_rate REAL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS market_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL,
                    market_title TEXT,
                    current_price REAL,
                    fair_value REAL,
                    edge REAL,
                    agent_name TEXT,
                    snapshot_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_trades_agent ON trades(agent_name);
                CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
                CREATE INDEX IF NOT EXISTS idx_trades_created ON trades(created_at);
                CREATE INDEX IF NOT EXISTS idx_logs_agent ON agent_logs(agent_name);
                CREATE INDEX IF NOT EXISTS idx_portfolio_time ON portfolio(recorded_at);
            """)

    def record_trade(self, trade: Dict) -> int:
        with self.get_cursor() as c:
            c.execute("""
                INSERT INTO trades 
                (agent_name, market_id, market_title, direction, entry_price, 
                 size, edge, confidence, reasoning, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade['agent_name'], trade['market_id'], trade.get('market_title', ''),
                trade['direction'], trade['entry_price'], trade['size'],
                trade.get('edge', 0), trade.get('confidence', 0),
                trade.get('reasoning', ''), json.dumps(trade.get('metadata', {}))
            ))
            return c.lastrowid

    def close_trade(self, trade_id: int, exit_price: float, profit_loss: float):
        with self.get_cursor() as c:
            c.execute("""
                UPDATE trades 
                SET exit_price = ?, profit_loss = ?, status = 'closed', 
                    closed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (exit_price, profit_loss, trade_id))

    def get_recent_trades(self, limit: int = 50) -> List[Dict]:
        with self.get_cursor() as c:
            c.execute("""
                SELECT * FROM trades ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in c.fetchall()]

    def get_open_positions(self) -> List[Dict]:
        with self.get_cursor() as c:
            c.execute("SELECT * FROM trades WHERE status = 'open'")
            return [dict(row) for row in c.fetchall()]

    def get_agent_stats(self, agent_name: str) -> Dict:
        with self.get_cursor() as c:
            c.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN profit_loss <= 0 THEN 1 ELSE 0 END) as losses,
                    SUM(profit_loss) as total_pnl,
                    AVG(profit_loss) as avg_pnl,
                    MAX(profit_loss) as best_trade,
                    MIN(profit_loss) as worst_trade
                FROM trades 
                WHERE agent_name = ? AND status = 'closed'
            """, (agent_name,))
            row = c.fetchone()
            if row:
                d = dict(row)
                total = d['total_trades'] or 0
                wins = d['wins'] or 0
                d['win_rate'] = (wins / total * 100) if total > 0 else 0
                return d
            return {}

    def get_all_stats(self) -> Dict:
        with self.get_cursor() as c:
            c.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(profit_loss) as total_pnl,
                    AVG(profit_loss) as avg_pnl
                FROM trades WHERE status = 'closed'
            """)
            row = c.fetchone()
            d = dict(row) if row else {}
            total = d.get('total_trades', 0) or 0
            wins = d.get('wins', 0) or 0
            d['win_rate'] = (wins / total * 100) if total > 0 else 0
            return d

    def get_daily_pnl(self, days: int = 30) -> List[Dict]:
        with self.get_cursor() as c:
            c.execute("""
                SELECT 
                    DATE(closed_at) as date,
                    SUM(profit_loss) as daily_pnl,
                    COUNT(*) as trades_count
                FROM trades 
                WHERE status = 'closed' 
                    AND closed_at >= datetime('now', ?)
                GROUP BY DATE(closed_at)
                ORDER BY date
            """, (f'-{days} days',))
            return [dict(row) for row in c.fetchall()]

    def get_cumulative_pnl(self) -> List[Dict]:
        with self.get_cursor() as c:
            c.execute("""
                SELECT 
                    DATE(closed_at) as date,
                    SUM(profit_loss) as daily_pnl
                FROM trades 
                WHERE status = 'closed'
                GROUP BY DATE(closed_at)
                ORDER BY date
            """)
            rows = [dict(row) for row in c.fetchall()]
            cumulative = 0
            result = []
            for row in rows:
                cumulative += row['daily_pnl'] or 0
                result.append({
                    'date': row['date'],
                    'daily_pnl': row['daily_pnl'],
                    'cumulative_pnl': cumulative
                })
            return result

    def record_portfolio_snapshot(self, snapshot: Dict):
        with self.get_cursor() as c:
            c.execute("""
                INSERT INTO portfolio 
                (total_balance, available_balance, total_pnl, daily_pnl, 
                 open_positions, win_rate)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                snapshot['total_balance'], snapshot['available_balance'],
                snapshot['total_pnl'], snapshot['daily_pnl'],
                snapshot['open_positions'], snapshot.get('win_rate', 0)
            ))

    def log_agent(self, agent_name: str, level: str, message: str, data: Dict = None):
        with self.get_cursor() as c:
            c.execute("""
                INSERT INTO agent_logs (agent_name, level, message, data)
                VALUES (?, ?, ?, ?)
            """, (agent_name, level, message, json.dumps(data) if data else None))

    def get_agent_logs(self, agent_name: str = None, limit: int = 100) -> List[Dict]:
        with self.get_cursor() as c:
            if agent_name:
                c.execute("""
                    SELECT * FROM agent_logs 
                    WHERE agent_name = ? 
                    ORDER BY created_at DESC LIMIT ?
                """, (agent_name, limit))
            else:
                c.execute("""
                    SELECT * FROM agent_logs 
                    ORDER BY created_at DESC LIMIT ?
                """, (limit,))
            return [dict(row) for row in c.fetchall()]

    def get_daily_loss(self) -> float:
        with self.get_cursor() as c:
            c.execute("""
                SELECT COALESCE(SUM(profit_loss), 0) as daily_loss
                FROM trades 
                WHERE status = 'closed' 
                    AND DATE(closed_at) = DATE('now')
                    AND profit_loss < 0
            """)
            row = c.fetchone()
            return abs(dict(row)['daily_loss']) if row else 0


db = Database()

import sqlite3

import json

import threading

from datetime import datetime

from typing import Dict, List, Optional

from contextlib import contextmanager





class Database:

    _local = threading.local()



    def __init__(self, db_path: str = "polymarket_bot.db"):

        self.db_path = db_path

        self._init_db()



    def _get_conn(self):

        if not hasattr(self._local, 'conn') or self._local.conn is None:

            self._local.conn = sqlite3.connect(self.db_path, timeout=10)

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

                    strategy TEXT DEFAULT 'info_arb',

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



                CREATE TABLE IF NOT EXISTS activity_stream (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    agent_name TEXT NOT NULL,

                    action TEXT NOT NULL,

                    detail TEXT,

                    icon TEXT DEFAULT '🔄',

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

                );



                CREATE TABLE IF NOT EXISTS settings (

                    key TEXT PRIMARY KEY,

                    value TEXT NOT NULL,

                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

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



                CREATE INDEX IF NOT EXISTS idx_trades_agent ON trades(agent_name);

                CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);

                CREATE INDEX IF NOT EXISTS idx_trades_created ON trades(created_at);

                CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy);

                CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_stream(created_at);

            """)



    # === Settings ===

    def save_setting(self, key: str, value) -> None:

        with self.get_cursor() as c:

            c.execute("""

                INSERT INTO settings (key, value, updated_at)

                VALUES (?, ?, CURRENT_TIMESTAMP)

                ON CONFLICT(key) DO UPDATE SET value=?, updated_at=CURRENT_TIMESTAMP

            """, (key, json.dumps(value), json.dumps(value)))



    def get_setting(self, key: str, default=None):

        with self.get_cursor() as c:

            c.execute("SELECT value FROM settings WHERE key=?", (key,))

            row = c.fetchone()

            if row:

                try:

                    return json.loads(row['value'])

                except (json.JSONDecodeError, TypeError):

                    return row['value']

            return default



    def get_all_settings(self) -> Dict:

        with self.get_cursor() as c:

            c.execute("SELECT key, value FROM settings")

            result = {}

            for row in c.fetchall():

                try:

                    result[row['key']] = json.loads(row['value'])

                except (json.JSONDecodeError, TypeError):

                    result[row['key']] = row['value']

            return result



    # === Activity Stream ===

    def add_activity(self, agent_name: str, action: str, detail: str = "", icon: str = "🔄") -> int:

        with self.get_cursor() as c:

            c.execute("INSERT INTO activity_stream (agent_name, action, detail, icon) VALUES (?,?,?,?)",

                      (agent_name, action, detail, icon))

            # keep only last 500

            c.execute("DELETE FROM activity_stream WHERE id NOT IN (SELECT id FROM activity_stream ORDER BY created_at DESC LIMIT 500)")

            return c.lastrowid



    def get_activities(self, limit: int = 50) -> List[Dict]:

        with self.get_cursor() as c:

            c.execute("SELECT * FROM activity_stream ORDER BY created_at DESC LIMIT ?", (limit,))

            return [dict(row) for row in c.fetchall()]



    # === Trades ===

    def record_trade(self, trade: Dict) -> int:

        with self.get_cursor() as c:

            c.execute("""

                INSERT INTO trades

                (agent_name, market_id, market_title, direction, entry_price,

                 size, edge, confidence, reasoning, strategy, metadata)

                VALUES (?,?,?,?,?,?,?,?,?,?,?)

            """, (

                trade['agent_name'], trade['market_id'], trade.get('market_title', ''),

                trade['direction'], trade['entry_price'], trade['size'],

                trade.get('edge', 0), trade.get('confidence', 0),

                trade.get('reasoning', ''), trade.get('strategy', 'info_arb'),

                json.dumps(trade.get('metadata', {}))

            ))

            return c.lastrowid



    def close_trade(self, trade_id: int, exit_price: float, profit_loss: float):

        with self.get_cursor() as c:

            c.execute("UPDATE trades SET exit_price=?, profit_loss=?, status='closed', closed_at=CURRENT_TIMESTAMP WHERE id=?",

                      (exit_price, profit_loss, trade_id))



    def get_recent_trades(self, limit: int = 50) -> List[Dict]:

        with self.get_cursor() as c:

            c.execute("SELECT * FROM trades ORDER BY created_at DESC LIMIT ?", (limit,))

            return [dict(row) for row in c.fetchall()]



    def get_open_positions(self) -> List[Dict]:

        with self.get_cursor() as c:

            c.execute("SELECT * FROM trades WHERE status='open'")

            return [dict(row) for row in c.fetchall()]



    def get_agent_stats(self, agent_name: str) -> Dict:

        with self.get_cursor() as c:

            c.execute("""

                SELECT COUNT(*) as total_trades,

                    SUM(CASE WHEN profit_loss>0 THEN 1 ELSE 0 END) as wins,

                    COALESCE(SUM(profit_loss),0) as total_pnl,

                    COALESCE(AVG(profit_loss),0) as avg_pnl,

                    COALESCE(MAX(profit_loss),0) as best_trade,

                    COALESCE(MIN(profit_loss),0) as worst_trade

                FROM trades WHERE agent_name=? AND status='closed'

            """, (agent_name,))

            row = c.fetchone()

            d = dict(row) if row else {}

            total = d.get('total_trades', 0) or 0

            wins = d.get('wins', 0) or 0

            d['win_rate'] = (wins / total * 100) if total > 0 else 0

            return d



    def get_all_stats(self) -> Dict:

        with self.get_cursor() as c:

            c.execute("""

                SELECT COUNT(*) as total_trades,

                    SUM(CASE WHEN profit_loss>0 THEN 1 ELSE 0 END) as wins,

                    COALESCE(SUM(profit_loss),0) as total_pnl,

                    COALESCE(AVG(profit_loss),0) as avg_pnl

                FROM trades WHERE status='closed'

            """)

            row = c.fetchone()

            d = dict(row) if row else {}

            total = d.get('total_trades', 0) or 0

            wins = d.get('wins', 0) or 0

            d['win_rate'] = (wins / total * 100) if total > 0 else 0

            return d



    def get_strategy_stats(self) -> Dict:

        """按策略统计"""

        with self.get_cursor() as c:

            c.execute("""

                SELECT strategy,

                    COUNT(*) as trades,

                    SUM(CASE WHEN profit_loss>0 THEN 1 ELSE 0 END) as wins,

                    COALESCE(SUM(profit_loss),0) as pnl

                FROM trades WHERE status='closed'

                GROUP BY strategy

            """)

            result = {}

            for row in c.fetchall():

                d = dict(row)

                t = d['trades'] or 0

                w = d['wins'] or 0

                d['win_rate'] = (w / t * 100) if t > 0 else 0

                result[d['strategy'] or 'unknown'] = d

            return result



    def get_daily_pnl(self, days: int = 30) -> List[Dict]:

        with self.get_cursor() as c:

            c.execute("""

                SELECT DATE(closed_at) as date, SUM(profit_loss) as daily_pnl, COUNT(*) as trades_count

                FROM trades WHERE status='closed' AND closed_at>=datetime('now',?)

                GROUP BY DATE(closed_at) ORDER BY date

            """, (f'-{days} days',))

            return [dict(row) for row in c.fetchall()]



    def get_cumulative_pnl(self) -> List[Dict]:

        with self.get_cursor() as c:

            c.execute("""

                SELECT DATE(closed_at) as date, SUM(profit_loss) as daily_pnl

                FROM trades WHERE status='closed' GROUP BY DATE(closed_at) ORDER BY date

            """)

            rows = [dict(row) for row in c.fetchall()]

            cum = 0

            result = []

            for row in rows:

                cum += row['daily_pnl'] or 0

                result.append({'date': row['date'], 'daily_pnl': row['daily_pnl'], 'cumulative_pnl': cum})

            return result



    def get_daily_loss(self) -> float:

        with self.get_cursor() as c:

            c.execute("""

                SELECT COALESCE(SUM(profit_loss),0) as loss

                FROM trades WHERE status='closed' AND DATE(closed_at)=DATE('now') AND profit_loss<0

            """)

            row = c.fetchone()

            return abs(dict(row)['loss']) if row else 0



    def get_today_pnl(self) -> float:

        with self.get_cursor() as c:

            c.execute("""

                SELECT COALESCE(SUM(profit_loss),0) as pnl

                FROM trades WHERE status='closed' AND DATE(closed_at)=DATE('now')

            """)

            row = c.fetchone()

            return dict(row)['pnl'] if row else 0



    def log_agent(self, agent_name: str, level: str, message: str, data: Dict = None):

        with self.get_cursor() as c:

            c.execute("INSERT INTO agent_logs (agent_name, level, message, data) VALUES (?,?,?,?)",

                      (agent_name, level, message, json.dumps(data) if data else None))



    def get_agent_logs(self, agent_name: str = None, limit: int = 100) -> List[Dict]:

        with self.get_cursor() as c:

            if agent_name:

                c.execute("SELECT * FROM agent_logs WHERE agent_name=? ORDER BY created_at DESC LIMIT ?", (agent_name, limit))

            else:

                c.execute("SELECT * FROM agent_logs ORDER BY created_at DESC LIMIT ?", (limit,))

            return [dict(row) for row in c.fetchall()]



    def record_portfolio_snapshot(self, snapshot: Dict):

        with self.get_cursor() as c:

            c.execute("""

                INSERT INTO portfolio (total_balance, available_balance, total_pnl, daily_pnl, open_positions, win_rate)

                VALUES (?,?,?,?,?,?)

            """, (snapshot['total_balance'], snapshot['available_balance'],

                  snapshot['total_pnl'], snapshot['daily_pnl'],

                  snapshot['open_positions'], snapshot.get('win_rate', 0)))





db = Database()


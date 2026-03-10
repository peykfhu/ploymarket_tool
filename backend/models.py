
from dataclasses import dataclass, field

from typing import Optional, Dict, Any, List

from datetime import datetime

from enum import Enum





class TradeDirection(Enum):

    BUY_YES = "BUY_YES"

    BUY_NO = "BUY_NO"

    SELL_YES = "SELL_YES"

    SELL_NO = "SELL_NO"





class TradeStatus(Enum):

    OPEN = "open"

    CLOSED = "closed"

    PENDING = "pending"

    CANCELLED = "cancelled"





class AgentStatus(Enum):

    RUNNING = "running"

    STOPPED = "stopped"

    ERROR = "error"

    PAUSED = "paused"





@dataclass

class Signal:

    agent_name: str

    market_id: str

    market_title: str

    direction: str

    entry_price: float

    fair_value: float

    edge: float

    confidence: float

    size: float

    reasoning: str

    metadata: Dict[str, Any] = field(default_factory=dict)

    timestamp: datetime = field(default_factory=datetime.utcnow)





@dataclass

class MarketData:

    market_id: str

    title: str

    yes_price: float

    no_price: float

    volume: float

    liquidity: float

    end_date: Optional[str] = None

    category: Optional[str] = None





@dataclass

class AgentState:

    name: str

    status: AgentStatus = AgentStatus.STOPPED

    total_trades: int = 0

    win_rate: float = 0.0

    total_pnl: float = 0.0

    last_signal: Optional[str] = None

    last_activity: Optional[datetime] = None

    errors: int = 0

    config: Dict = field(default_factory=dict)

    scan_count: int = 0

    opportunities_found: int = 0


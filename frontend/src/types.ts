// frontend/src/types.ts
export interface AgentState {
  name: string;
  status: 'running' | 'stopped' | 'error' | 'paused';
  total_trades: number;
  win_rate: number;
  total_pnl: number;
  best_trade: number;
  worst_trade: number;
  last_signal: string | null;
  last_activity: string | null;
  errors: number;
  interval: number;
}

export interface Trade {
  id: number;
  agent_name: string;
  market_id: string;
  market_title: string;
  direction: string;
  entry_price: number;
  exit_price: number | null;
  size: number;
  profit_loss: number;
  status: 'open' | 'closed';
  edge: number;
  confidence: number;
  reasoning: string;
  created_at: string;
  closed_at: string | null;
}

export interface DashboardData {
  overview: {
    initial_balance: number;
    current_balance: number;
    total_pnl: number;
    total_trades: number;
    win_rate: number;
    open_positions: number;
    roi: number;
  };
  agents: Record<string, AgentState>;
  recent_trades: Trade[];
  open_positions: Trade[];
  cumulative_pnl: { date: string; daily_pnl: number; cumulative_pnl: number }[];
  daily_pnl: { date: string; daily_pnl: number; trades_count: number }[];
}

export interface WsMessage {
  type: string;
  timestamp: string;
  balance: number;
  total_pnl: number;
  total_trades: number;
  win_rate: number;
  open_positions: number;
  agents: Record<string, AgentState>;
  recent_trades: Trade[];
  recent_logs: any[];
}

export interface LogEntry {
  id: number;
  agent_name: string;
  level: string;
  message: string;
  data: string | null;
  created_at: string;
}
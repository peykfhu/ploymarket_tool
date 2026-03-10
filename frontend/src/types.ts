
export interface AgentState {

  name: string; status: string; total_trades: number; win_rate: number;

  total_pnl: number; best_trade: number; worst_trade: number;

  last_signal: string | null; last_activity: string | null;

  errors: number; interval: number; scan_count: number; opportunities_found: number;

}

export interface Trade {

  id: number; agent_name: string; market_id: string; market_title: string;

  direction: string; entry_price: number; exit_price: number | null;

  size: number; profit_loss: number; status: string; edge: number;

  confidence: number; reasoning: string; strategy: string;

  created_at: string; closed_at: string | null;

}

export interface Activity {

  id: number; agent_name: string; action: string; detail: string;

  icon: string; created_at: string;

}

export interface ScannedMarket {

  id: string; question: string; yes_price: number | null;

  volume: number; end_date: string;

}

export interface DashboardData {

  overview: {

    initial_balance: number; current_balance: number; real_balance: number | null;

    total_pnl: number; today_pnl: number; total_trades: number;

    win_rate: number; open_positions: number; roi: number;

  };

  strategy_stats: Record<string, { trades: number; wins: number; pnl: number; win_rate: number }>;

  agents: Record<string, AgentState>;

  recent_trades: Trade[]; open_positions: Trade[];

  cumulative_pnl: { date: string; cumulative_pnl: number }[];

  daily_pnl: { date: string; daily_pnl: number }[];

  activities: Activity[]; dry_run: boolean;

}

export interface WsMessage {

  type: string; balance: number; total_pnl: number; today_pnl: number;

  total_trades: number; win_rate: number; open_positions: number;

  dry_run: boolean; agents: Record<string, AgentState>;

  recent_trades: Trade[]; activities: Activity[];

}

export interface Settings {

  max_position_size: number; max_daily_loss: number; min_edge: number;

  max_concurrent: number; stop_loss: number; daily_drawdown_limit: number;

  initial_balance: number; dry_run: boolean;

  interval_weather: number; interval_crypto: number; interval_politics: number;

  interval_sports: number; interval_endgame: number; interval_sports_endgame: number;

}


// frontend/src/components/LiveTicker.tsx
import React from 'react';
import { Trade } from '../types';

interface Props {
  trades: Trade[];
}

export function LiveTicker({ trades }: Props) {
  const recentTrades = trades.slice(0, 5);

  if (recentTrades.length === 0) return null;

  return (
    <div className="bg-gray-900 rounded-2xl p-4 border border-gray-800">
      <div className="flex items-center gap-2 mb-3">
        <div className="pulse-dot green"></div>
        <span className="text-sm font-medium text-gray-400">实时信号流</span>
      </div>

      <div className="space-y-2">
        {recentTrades.map((trade, i) => {
          const isNew = i === 0;
          return (
            <div
              key={trade.id}
              className={`
                flex items-center justify-between p-3 rounded-lg
                ${isNew ? 'bg-indigo-900/20 border border-indigo-800/30' : 'bg-gray-800/50'}
                transition-all duration-500
              `}
            >
              <div className="flex items-center gap-3">
                <span className="text-sm">
                  {trade.agent_name.includes('气象') ? '🌦️' :
                   trade.agent_name.includes('BTC') ? '₿' :
                   trade.agent_name.includes('民调') ? '🏛️' : '🏥'}
                </span>
                <div>
                  <div className="text-sm text-gray-300 font-medium">
                    {trade.reasoning || trade.market_title?.slice(0, 60)}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {trade.agent_name} · {new Date(trade.created_at).toLocaleTimeString('zh-CN')}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span className={`text-xs px-2 py-0.5 rounded ${
                  trade.direction.includes('YES')
                    ? 'bg-green-900/30 text-green-400'
                    : 'bg-red-900/30 text-red-400'
                }`}>
                  {trade.direction}
                </span>
                <span className="text-sm font-mono text-indigo-400">
                  {(trade.edge * 100).toFixed(1)}%
                </span>
                <span className="text-sm font-mono text-white font-bold">
                  ${trade.size.toFixed(2)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
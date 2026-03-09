// frontend/src/components/TradeLog.tsx
import React from 'react';
import { Trade } from '../types';

interface Props {
  trades: Trade[];
}

export function TradeLog({ trades }: Props) {
  if (trades.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <div className="text-3xl mb-2">📭</div>
        <p>暂无交易记录</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800">
            <th className="text-left py-3 px-2 text-gray-500 font-medium">时间</th>
            <th className="text-left py-3 px-2 text-gray-500 font-medium">Agent</th>
            <th className="text-left py-3 px-2 text-gray-500 font-medium">市场</th>
            <th className="text-left py-3 px-2 text-gray-500 font-medium">方向</th>
            <th className="text-right py-3 px-2 text-gray-500 font-medium">价格</th>
            <th className="text-right py-3 px-2 text-gray-500 font-medium">仓位</th>
            <th className="text-right py-3 px-2 text-gray-500 font-medium">边际</th>
            <th className="text-right py-3 px-2 text-gray-500 font-medium">盈亏</th>
            <th className="text-center py-3 px-2 text-gray-500 font-medium">状态</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade) => {
            const isProfit = trade.profit_loss >= 0;
            const directionEmoji = trade.direction.includes('YES') ? '🟢' : '🔴';

            return (
              <tr
                key={trade.id}
                className="border-b border-gray-800/50 hover:bg-gray-800/30 transition"
              >
                <td className="py-3 px-2 text-gray-400 text-xs whitespace-nowrap">
                  {new Date(trade.created_at).toLocaleString('zh-CN', {
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </td>
                <td className="py-3 px-2">
                  <span className="text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded">
                    {trade.agent_name.split(' ')[0]}
                  </span>
                </td>
                <td className="py-3 px-2 text-gray-300 max-w-[200px] truncate" title={trade.market_title}>
                  {trade.market_title || trade.market_id}
                </td>
                <td className="py-3 px-2">
                  <span className="flex items-center gap-1">
                    {directionEmoji}
                    <span className="text-xs text-gray-400">{trade.direction}</span>
                  </span>
                </td>
                <td className="py-3 px-2 text-right text-gray-300 font-mono">
                  ${trade.entry_price.toFixed(4)}
                </td>
                <td className="py-3 px-2 text-right text-gray-300 font-mono">
                  ${trade.size.toFixed(2)}
                </td>
                <td className="py-3 px-2 text-right">
                  <span className="text-indigo-400 font-mono">
                    {(trade.edge * 100).toFixed(1)}%
                  </span>
                </td>
                <td className={`py-3 px-2 text-right font-mono font-bold ${
                  trade.status === 'open'
                    ? 'text-yellow-400'
                    : isProfit
                    ? 'text-green-400'
                    : 'text-red-400'
                }`}>
                  {trade.status === 'open'
                    ? '持仓中'
                    : `${isProfit ? '+' : ''}$${trade.profit_loss.toFixed(2)}`
                  }
                </td>
                <td className="py-3 px-2 text-center">
                  <span className={`
                    px-2 py-0.5 rounded-full text-xs font-medium
                    ${trade.status === 'open'
                      ? 'bg-yellow-900/30 text-yellow-400'
                      : isProfit
                      ? 'bg-green-900/30 text-green-400'
                      : 'bg-red-900/30 text-red-400'
                    }
                  `}>
                    {trade.status === 'open' ? '⚡ Open' : isProfit ? '✅ Win' : '❌ Loss'}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
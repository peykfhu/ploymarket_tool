// frontend/src/components/Dashboard.tsx
import React, { useState } from 'react';
import { DashboardData, AgentState, Trade } from '../types';
import { AgentCard } from './AgentCard';
import { TradeLog } from './TradeLog';
import { ProfitChart } from './ProfitChart';
import { LiveTicker } from './LiveTicker';
import { RiskPanel } from './RiskPanel';
import { Header } from './Header';

interface Props {
  data: DashboardData;
  isConnected: boolean;
  onRefresh: () => void;
}

export function Dashboard({ data, isConnected, onRefresh }: Props) {
  const [activeTab, setActiveTab] = useState<'overview' | 'trades' | 'settings'>('overview');
  const { overview, agents, recent_trades, open_positions, cumulative_pnl, daily_pnl } = data;

  return (
    <div className="min-h-screen bg-gray-950">
      <Header isConnected={isConnected} onRefresh={onRefresh} />

      {/* 顶部统计卡片 */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
          <StatCard
            label="总资金"
            value={`$${overview.current_balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
            change={overview.total_pnl}
            icon="💰"
          />
          <StatCard
            label="总盈亏"
            value={`$${overview.total_pnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
            isPositive={overview.total_pnl >= 0}
            icon="📈"
          />
          <StatCard
            label="ROI"
            value={`${overview.roi.toFixed(1)}%`}
            isPositive={overview.roi >= 0}
            icon="🎯"
          />
          <StatCard
            label="总交易"
            value={overview.total_trades.toString()}
            icon="🔄"
          />
          <StatCard
            label="胜率"
            value={`${overview.win_rate.toFixed(1)}%`}
            isPositive={overview.win_rate >= 50}
            icon="✅"
          />
          <StatCard
            label="持仓中"
            value={overview.open_positions.toString()}
            icon="📊"
          />
        </div>

        {/* 标签页 */}
        <div className="flex gap-2 mb-6">
          {(['overview', 'trades', 'settings'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg font-medium transition ${
                activeTab === tab
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {tab === 'overview' ? '📊 总览' : tab === 'trades' ? '📋 交易' : '⚙️ 设置'}
            </button>
          ))}
        </div>

        {activeTab === 'overview' && (
          <>
            {/* Agent 状态卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              {Object.entries(agents).map(([key, agent]) => (
                <AgentCard key={key} agentKey={key} agent={agent} />
              ))}
            </div>

            {/* 图表区域 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
                <h3 className="text-lg font-bold text-white mb-4">📈 累计盈亏</h3>
                <ProfitChart data={cumulative_pnl} />
              </div>
              <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
                <h3 className="text-lg font-bold text-white mb-4">📊 每日盈亏</h3>
                <ProfitChart data={daily_pnl} type="bar" />
              </div>
            </div>

            {/* 实时滚动 */}
            <LiveTicker trades={recent_trades} />

            {/* 最近交易 */}
            <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800 mt-6">
              <h3 className="text-lg font-bold text-white mb-4">🔄 最近交易</h3>
              <TradeLog trades={recent_trades.slice(0, 15)} />
            </div>
          </>
        )}

        {activeTab === 'trades' && (
          <div className="space-y-6">
            {open_positions.length > 0 && (
              <div className="bg-gray-900 rounded-2xl p-6 border border-yellow-800/30">
                <h3 className="text-lg font-bold text-yellow-400 mb-4">
                  ⚡ 当前持仓 ({open_positions.length})
                </h3>
                <TradeLog trades={open_positions} />
              </div>
            )}
            <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
              <h3 className="text-lg font-bold text-white mb-4">📋 全部交易记录</h3>
              <TradeLog trades={recent_trades} />
            </div>
          </div>
        )}

        {activeTab === 'settings' && <RiskPanel />}
      </div>
    </div>
  );
}

// 统计卡片组件
function StatCard({
  label,
  value,
  change,
  isPositive,
  icon,
}: {
  label: string;
  value: string;
  change?: number;
  isPositive?: boolean;
  icon: string;
}) {
  const color = isPositive === undefined
    ? 'text-white'
    : isPositive
    ? 'text-green-400'
    : 'text-red-400';

  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 hover:border-gray-700 transition">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">{icon}</span>
        <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
      </div>
      <div className={`text-xl font-bold ${color} animate-count`}>
        {value}
      </div>
      {change !== undefined && (
        <div className={`text-xs mt-1 ${change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
          {change >= 0 ? '+' : ''}{change.toFixed(2)}
        </div>
      )}
    </div>
  );
}
// frontend/src/components/AgentCard.tsx
import React from 'react';
import { AgentState } from '../types';
import { startAgent, stopAgent } from '../api';

interface Props {
  agentKey: string;
  agent: AgentState;
}

const agentIcons: Record<string, string> = {
  weather: '🌦️',
  crypto: '₿',
  politics: '🏛️',
  sports: '🏥',
};

const agentColors: Record<string, string> = {
  weather: 'from-blue-600 to-cyan-600',
  crypto: 'from-orange-600 to-yellow-600',
  politics: 'from-purple-600 to-pink-600',
  sports: 'from-green-600 to-emerald-600',
};

export function AgentCard({ agentKey, agent }: Props) {
  const icon = agentIcons[agentKey] || '🤖';
  const gradient = agentColors[agentKey] || 'from-gray-600 to-gray-700';
  const isRunning = agent.status === 'running';

  async function toggleAgent() {
    try {
      if (isRunning) {
        await stopAgent(agentKey);
      } else {
        await startAgent(agentKey);
      }
    } catch (e) {
      console.error('Failed to toggle agent', e);
    }
  }

  return (
    <div className={`
      bg-gray-900 rounded-2xl p-5 border border-gray-800
      hover:border-gray-700 transition-all duration-300
      ${isRunning ? 'ring-1 ring-indigo-500/20' : ''}
    `}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`
            w-10 h-10 rounded-xl bg-gradient-to-br ${gradient}
            flex items-center justify-center text-lg
          `}>
            {icon}
          </div>
          <div>
            <h3 className="font-semibold text-white text-sm">{agent.name}</h3>
            <div className="flex items-center gap-1.5 mt-0.5">
              <div className={`pulse-dot ${
                isRunning ? 'green' : agent.status === 'error' ? 'red' : 'yellow'
              }`}></div>
              <span className={`text-xs ${
                isRunning ? 'text-green-400' : 'text-gray-500'
              }`}>
                {isRunning ? '运行中' : agent.status === 'error' ? '错误' : '已停止'}
              </span>
            </div>
          </div>
        </div>

        <button
          onClick={toggleAgent}
          className={`
            px-3 py-1.5 rounded-lg text-xs font-medium transition
            ${isRunning
              ? 'bg-red-900/30 text-red-400 hover:bg-red-900/50'
              : 'bg-green-900/30 text-green-400 hover:bg-green-900/50'
            }
          `}
        >
          {isRunning ? '停止' : '启动'}
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <div className="text-xs text-gray-500">交易</div>
          <div className="text-lg font-bold text-white">{agent.total_trades}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">胜率</div>
          <div className={`text-lg font-bold ${
            agent.win_rate >= 60 ? 'text-green-400' : 
            agent.win_rate >= 40 ? 'text-yellow-400' : 'text-red-400'
          }`}>
            {agent.win_rate.toFixed(0)}%
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500">盈亏</div>
          <div className={`text-lg font-bold ${
            (agent.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
          }`}>
            ${(agent.total_pnl || 0).toFixed(0)}
          </div>
        </div>
      </div>

      {/* Last Signal */}
      {agent.last_signal && (
        <div className="mt-3 p-2 bg-gray-800/50 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">最新信号</div>
          <div className="text-xs text-gray-300 truncate">
            {agent.last_signal}
          </div>
        </div>
      )}

      {/* Errors */}
      {agent.errors > 0 && (
        <div className="mt-2 text-xs text-red-400">
          ⚠️ {agent.errors} 个错误
        </div>
      )}
    </div>
  );
}
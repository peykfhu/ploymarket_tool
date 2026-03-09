// frontend/src/components/Header.tsx
import React from 'react';

interface Props {
  isConnected: boolean;
  onRefresh: () => void;
}

export function Header({ isConnected, onRefresh }: Props) {
  return (
    <header className="bg-gray-900/80 backdrop-blur-xl border-b border-gray-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🤖</span>
          <div>
            <h1 className="text-lg font-bold text-white">
              Polymarket 套利系统
            </h1>
            <p className="text-xs text-gray-500">4 Agents · 全天候自动运行</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* 连接状态 */}
          <div className="flex items-center gap-2">
            <div className={`pulse-dot ${isConnected ? 'green' : 'red'}`}></div>
            <span className={`text-xs ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
              {isConnected ? '实时连接' : '断开连接'}
            </span>
          </div>

          {/* DRY RUN 标识 */}
          <span className="px-2 py-1 rounded text-xs font-medium bg-yellow-900/30 text-yellow-400 border border-yellow-800/30">
            DRY RUN
          </span>

          <button
            onClick={onRefresh}
            className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition text-gray-400 hover:text-white"
            title="刷新"
          >
            🔄
          </button>
        </div>
      </div>
    </header>
  );
}

import React from 'react';



interface Props {

  isConnected: boolean;

  isDryRun: boolean;

  onRefresh: () => void;

}



export function Header({ isConnected, isDryRun, onRefresh }: Props) {

  return (

    <header className="bg-gray-900/90 backdrop-blur-xl border-b border-gray-800 sticky top-0 z-50">

      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">

        <div className="flex items-center gap-3">

          <span className="text-2xl">🤖</span>

          <div>

            <h1 className="text-lg font-bold text-white">Polymarket 套利系统</h1>

            <p className="text-xs text-gray-500">4 Agents · 全天候自动运行</p>

          </div>

        </div>

        <div className="flex items-center gap-3">

          <div className="flex items-center gap-1.5">

            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />

            <span className={`text-xs ${isConnected ? 'text-green-400' : 'text-red-400'}`}>

              {isConnected ? '实时' : '断开'}

            </span>

          </div>

          <span className={`px-2 py-1 rounded text-xs font-bold ${isDryRun ? 'bg-yellow-900/40 text-yellow-400 border border-yellow-700/50' : 'bg-red-900/40 text-red-400 border border-red-700/50 animate-pulse'}`}>

            {isDryRun ? '🧪 模拟' : '🔴 实盘'}

          </span>

          <button onClick={onRefresh} className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-all active:scale-90 text-gray-400 hover:text-white">🔄</button>

        </div>

      </div>

    </header>

  );

}


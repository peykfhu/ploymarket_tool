// frontend/src/App.tsx
import React, { useState, useEffect } from 'react';
import { Dashboard } from './components/Dashboard';
import { DashboardData } from './types';
import { fetchDashboard } from './api';
import { useWebSocket } from './hooks/useWebSocket';

function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const wsUrl = `ws://${window.location.hostname}:8899/ws`;
  const { lastMessage, isConnected } = useWebSocket(wsUrl);

  useEffect(() => {
    loadDashboard();
    const interval = setInterval(loadDashboard, 30000); // 30秒刷新
    return () => clearInterval(interval);
  }, []);

  async function loadDashboard() {
    try {
      const result = await fetchDashboard();
      setData(result);
      setError(null);
    } catch (e) {
      setError('无法连接到后端服务');
    } finally {
      setLoading(false);
    }
  }

  // 用WebSocket数据更新实时部分
  useEffect(() => {
    if (lastMessage && data) {
      setData(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          overview: {
            ...prev.overview,
            current_balance: lastMessage.balance,
            total_pnl: lastMessage.total_pnl,
            total_trades: lastMessage.total_trades,
            win_rate: lastMessage.win_rate,
            open_positions: lastMessage.open_positions,
          },
          agents: lastMessage.agents || prev.agents,
          recent_trades: lastMessage.recent_trades || prev.recent_trades,
        };
      });
    }
  }, [lastMessage]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-indigo-500 mx-auto mb-4"></div>
          <p className="text-gray-400 text-lg">加载中...</p>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center bg-gray-900 rounded-2xl p-8 max-w-md">
          <div className="text-red-400 text-5xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold text-white mb-2">连接失败</h2>
          <p className="text-gray-400 mb-4">{error}</p>
          <p className="text-gray-500 text-sm mb-4">
            确保后端服务运行在端口 8899
          </p>
          <button
            onClick={loadDashboard}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg transition"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <Dashboard
      data={data!}
      isConnected={isConnected}
      onRefresh={loadDashboard}
    />
  );
}

export default App;
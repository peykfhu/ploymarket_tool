
import React, { useState, useEffect } from 'react';

import { Dashboard } from './components/Dashboard';

import { DashboardData } from './types';

import { fetchDashboard } from './api';

import { useWebSocket } from './hooks/useWebSocket';



function App() {

  const [data, setData] = useState<DashboardData | null>(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState<string | null>(null);



  const wsUrl = `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.hostname}:8899/ws`;

  const { lastMessage, isConnected } = useWebSocket(wsUrl);



  useEffect(() => { load(); const i = setInterval(load, 15000); return () => clearInterval(i); }, []);



  async function load() {

    try { setData(await fetchDashboard()); setError(null); }

    catch { setError('无法连接后端'); }

    finally { setLoading(false); }

  }



  useEffect(() => {

    if (lastMessage && data) {

      setData(prev => prev ? {

        ...prev,

        overview: { ...prev.overview, current_balance: lastMessage.balance, total_pnl: lastMessage.total_pnl,

          today_pnl: lastMessage.today_pnl, total_trades: lastMessage.total_trades,

          win_rate: lastMessage.win_rate, open_positions: lastMessage.open_positions },

        agents: lastMessage.agents || prev.agents,

        recent_trades: lastMessage.recent_trades || prev.recent_trades,

        activities: lastMessage.activities || prev.activities,

        dry_run: lastMessage.dry_run ?? prev.dry_run,

      } : prev);

    }

  }, [lastMessage]);



  if (loading) return (

    <div className="min-h-screen bg-gray-950 flex items-center justify-center">

      <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />

    </div>

  );



  if (error && !data) return (

    <div className="min-h-screen bg-gray-950 flex items-center justify-center">

      <div className="bg-gray-900 rounded-2xl p-8 text-center">

        <div className="text-4xl mb-3">⚠️</div>

        <p className="text-white mb-2">{error}</p>

        <button onClick={load} className="bg-indigo-600 text-white px-4 py-2 rounded-lg active:scale-95">重试</button>

      </div>

    </div>

  );



  return <Dashboard data={data!} isConnected={isConnected} onRefresh={load} />;

}



export default App;


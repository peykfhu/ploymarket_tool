
import { useState, useEffect, useCallback } from 'react';

import { AgentState, DashboardData } from '../types';

import { fetchDashboard, fetchAgents } from '../api';



export function useAgentData(refreshInterval: number = 30000) {

  const [data, setData] = useState<DashboardData | null>(null);

  const [agents, setAgents] = useState<Record<string, AgentState>>({});

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState<string | null>(null);



  const refresh = useCallback(async () => {

    try {

      const [dashboardData, agentsData] = await Promise.all([

        fetchDashboard(),

        fetchAgents(),

      ]);

      setData(dashboardData);

      setAgents(agentsData);

      setError(null);

    } catch (e) {

      setError(e instanceof Error ? e.message : '数据加载失败');

    } finally {

      setLoading(false);

    }

  }, []);



  useEffect(() => {

    refresh();

    const interval = setInterval(refresh, refreshInterval);

    return () => clearInterval(interval);

  }, [refresh, refreshInterval]);



  return { data, agents, loading, error, refresh };

}


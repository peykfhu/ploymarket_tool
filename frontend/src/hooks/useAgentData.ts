
import { useState, useEffect, useCallback } from 'react';

import { DashboardData } from '../types';

import { fetchDashboard } from '../api';



export function useAgentData(refreshInterval = 30000) {

  const [data, setData] = useState<DashboardData | null>(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState<string | null>(null);



  const refresh = useCallback(async () => {

    try {

      const d = await fetchDashboard();

      setData(d);

      setError(null);

    } catch (e) {

      setError(e instanceof Error ? e.message : '加载失败');

    } finally {

      setLoading(false);

    }

  }, []);



  useEffect(() => {

    refresh();

    const i = setInterval(refresh, refreshInterval);

    return () => clearInterval(i);

  }, [refresh, refreshInterval]);



  return { data, loading, error, refresh };

}


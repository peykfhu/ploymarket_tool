
import { useState, useEffect, useRef, useCallback } from 'react';

import { WsMessage } from '../types';



export function useWebSocket(url: string) {

  const [lastMessage, setLastMessage] = useState<WsMessage | null>(null);

  const [isConnected, setIsConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);

  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();



  const connect = useCallback(() => {

    try {

      const ws = new WebSocket(url);

      ws.onopen = () => setIsConnected(true);

      ws.onmessage = (e) => {

        try {

          const data = JSON.parse(e.data);

          if (data.type === 'update') setLastMessage(data);

        } catch {}

      };

      ws.onclose = () => {

        setIsConnected(false);

        reconnectTimer.current = setTimeout(connect, 3000);

      };

      ws.onerror = () => ws.close();

      wsRef.current = ws;

    } catch {

      reconnectTimer.current = setTimeout(connect, 3000);

    }

  }, [url]);



  useEffect(() => {

    connect();

    return () => {

      if (wsRef.current) wsRef.current.close();

      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);

    };

  }, [connect]);



  return { lastMessage, isConnected };

}


// frontend/src/hooks/useWebSocket.ts
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

      ws.onopen = () => {
        setIsConnected(true);
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'update') {
            setLastMessage(data);
          }
        } catch (e) {
          console.error('Failed to parse WS message', e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket disconnected, reconnecting in 5s...');
        reconnectTimer.current = setTimeout(connect, 5000);
      };

      ws.onerror = (err) => {
        console.error('WebSocket error', err);
        ws.close();
      };

      wsRef.current = ws;
    } catch (e) {
      console.error('WebSocket connection failed', e);
      reconnectTimer.current = setTimeout(connect, 5000);
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
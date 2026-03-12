import { useState, useEffect, useRef, useCallback } from 'react';

export interface LogEvent {
  type: 'status' | 'thinking' | 'thought' | 'tool_call' | 'tool_result' | 'action' | 'final_answer' | 'error' | 'done';
  content?: string;
  tool?: string;
  input?: string;
  timestamp?: string;
}

interface UseWebSocketReturn {
  logs: LogEvent[];
  isConnected: boolean;
  isRunning: boolean;
  sendPrompt: (prompt: string) => void;
  clearLogs: () => void;
}

export function useWebSocket(url: string): UseWebSocketReturn {
  const [logs, setLogs] = useState<LogEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(url);

    ws.onopen = () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data: LogEvent = JSON.parse(event.data);
        setLogs((prev) => [...prev, data]);

        if (data.type === 'done' || data.type === 'final_answer') {
          setIsRunning(false);
        }
        if (data.type === 'error') {
          setIsRunning(false);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      setIsRunning(false);
      console.log('WebSocket disconnected, reconnecting in 3s...');
      reconnectTimerRef.current = setTimeout(connect, 3000);
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      ws.close();
    };

    wsRef.current = ws;
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const sendPrompt = useCallback((prompt: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      setIsRunning(true);
      setLogs([]);
      wsRef.current.send(JSON.stringify({ prompt }));
    }
  }, []);

  const clearLogs = useCallback(() => setLogs([]), []);

  return { logs, isConnected, isRunning, sendPrompt, clearLogs };
}

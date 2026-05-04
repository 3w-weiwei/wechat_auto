import { useEffect, useRef } from 'react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/appStore';

export function useWebSocket() {
  const setConnected = useAppStore((s) => s.setConnected);
  const setEngineStatus = useAppStore((s) => s.setEngineStatus);
  const addLog = useAppStore((s) => s.addLog);
  const didInit = useRef(false);

  useEffect(() => {
    if (didInit.current) return;
    didInit.current = true;

    apiClient.connect();

    const unsub1 = apiClient.on('connection', (evt) => {
      const c = !!evt.data?.connected;
      setConnected(c);
      if (c) addLog('success', '已连接到引擎服务');
    });

    const unsub2 = apiClient.on('engine.status', (evt) => {
      const status = (evt.data?.status as string) || 'not_found';
      setEngineStatus(status as 'ready' | 'error' | 'not_found' | 'minimized');
    });

    const unsub3 = apiClient.on('log', (evt) => {
      const level = (evt.data?.level as string) || 'info';
      const message = (evt.data?.message as string) || '';
      addLog(level as 'info' | 'error' | 'success', message);
    });

    return () => { unsub1(); unsub2(); unsub3(); apiClient.disconnect(); };
  }, [setConnected, setEngineStatus, addLog]);

  return {};
}

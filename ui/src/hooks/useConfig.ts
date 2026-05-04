import { useCallback } from 'react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/appStore';
import type { AttachmentStats } from '../types/models';

export function useConfig() {
  const { setAttachmentStats, addLog } = useAppStore();

  const fetchAttachmentStats = useCallback(async () => {
    try {
      const result = await apiClient.call('attachment.stats') as { stats: AttachmentStats };
      setAttachmentStats(result.stats);
    } catch { /* ignore */ }
  }, [setAttachmentStats]);

  const calibrate = useCallback(async () => {
    try {
      const result = await apiClient.call('engine.calibrate') as { status: string; dpi?: number };
      if (result.status === 'ready') {
        addLog('success', `校准完成 DPI=${result.dpi || '?'}`);
      } else {
        addLog('error', '校准失败：未找到微信窗口');
      }
      return result;
    } catch (e) {
      addLog('error', `校准失败: ${e}`);
      return null;
    }
  }, [addLog]);

  const cleanupAttachments = useCallback(async () => {
    try {
      const result = await apiClient.call('attachment.cleanup') as { removed: number };
      addLog('success', `已清理 ${result.removed} 个未引用附件`);
      await fetchAttachmentStats();
    } catch (e) {
      addLog('error', `清理失败: ${e}`);
    }
  }, [addLog, fetchAttachmentStats]);

  const openAttachmentDir = useCallback(async () => {
    try {
      await apiClient.call('attachment.open_dir');
    } catch (e) {
      addLog('error', `打开失败: ${e}`);
    }
  }, [addLog]);

  return { fetchAttachmentStats, calibrate, cleanupAttachments, openAttachmentDir };
}

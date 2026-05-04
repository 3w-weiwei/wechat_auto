import { useCallback } from 'react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/appStore';
import type { Task } from '../types/models';

export function useTasks() {
  const { tasks, setTasks, addTask, updateTask, removeTask, addLog } = useAppStore();

  const fetchTasks = useCallback(async () => {
    try {
      const result = await apiClient.call('task.list') as { tasks: Task[] };
      setTasks(result.tasks || []);
    } catch (e) {
      addLog('error', `加载任务失败: ${e}`);
    }
  }, [setTasks, addLog]);

  const createTasks = useCallback(async (params: Record<string, unknown>) => {
    try {
      const result = await apiClient.call('task.create', params) as { tasks: Task[] };
      (result.tasks || []).forEach((t: Task) => addTask(t));
      addLog('success', `成功创建 ${result.tasks?.length || 0} 个任务`);
      return result.tasks || [];
    } catch (e) {
      addLog('error', `创建任务失败: ${e}`);
      return [];
    }
  }, [addTask, addLog]);

  const editTask = useCallback(async (id: string, params: Record<string, unknown>) => {
    try {
      const result = await apiClient.call('task.update', { id, ...params }) as { task: Task };
      updateTask(result.task);
      addLog('success', '任务已更新');
      return result.task;
    } catch (e) {
      addLog('error', `更新任务失败: ${e}`);
      return null;
    }
  }, [updateTask, addLog]);

  const deleteTask = useCallback(async (id: string) => {
    try {
      await apiClient.call('task.delete', { id });
      removeTask(id);
      addLog('info', '任务已删除');
    } catch (e) {
      addLog('error', `删除任务失败: ${e}`);
    }
  }, [removeTask, addLog]);

  const toggleTask = useCallback(async (id: string) => {
    try {
      const result = await apiClient.call('task.toggle', { id }) as { active: boolean };
      const task = tasks.find((t) => t.id === id);
      if (task) updateTask({ ...task, active: result.active });
    } catch (e) {
      addLog('error', `操作失败: ${e}`);
    }
  }, [tasks, updateTask, addLog]);

  const runNow = useCallback(async (id: string) => {
    try {
      await apiClient.call('task.run_now', { id });
      addLog('info', '任务已加入执行队列');
    } catch (e) {
      addLog('error', `执行失败: ${e}`);
    }
  }, [addLog]);

  return { tasks, fetchTasks, createTasks, editTask, deleteTask, toggleTask, runNow };
}

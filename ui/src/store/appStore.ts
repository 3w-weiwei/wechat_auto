import { create } from 'zustand';
import type { Task, LogEntry, EngineStatus, AttachmentStats } from '../types/models';

interface AppState {
  // Connection
  connected: boolean;
  setConnected: (v: boolean) => void;

  // Tasks
  tasks: Task[];
  setTasks: (tasks: Task[]) => void;
  addTask: (task: Task) => void;
  updateTask: (task: Task) => void;
  removeTask: (id: string) => void;

  // Engine
  engineStatus: EngineStatus;
  setEngineStatus: (s: EngineStatus) => void;

  // Logs
  logs: LogEntry[];
  addLog: (level: LogEntry['level'], message: string) => void;
  clearLogs: () => void;

  // Attachments
  attachmentStats: AttachmentStats | null;
  setAttachmentStats: (s: AttachmentStats) => void;

  // UI
  activeTab: 'tasks' | 'create' | 'settings';
  setActiveTab: (t: 'tasks' | 'create' | 'settings') => void;
}

let logId = 0;

export const useAppStore = create<AppState>((set) => ({
  connected: false,
  setConnected: (v) => set({ connected: v }),

  tasks: [],
  setTasks: (tasks) => set({ tasks }),
  addTask: (task) => set((s) => ({ tasks: [task, ...s.tasks] })),
  updateTask: (task) => set((s) => ({
    tasks: s.tasks.map((t) => (t.id === task.id ? task : t)),
  })),
  removeTask: (id) => set((s) => ({ tasks: s.tasks.filter((t) => t.id !== id) })),

  engineStatus: 'ready',
  setEngineStatus: (status) => set({ engineStatus: status }),

  logs: [],
  addLog: (level, message) => set((s) => ({
    logs: [...s.logs.slice(-199), { id: ++logId, level, message, timestamp: new Date().toISOString() }],
  })),
  clearLogs: () => set({ logs: [] }),

  attachmentStats: null,
  setAttachmentStats: (stats) => set({ attachmentStats: stats }),

  activeTab: 'tasks',
  setActiveTab: (tab) => set({ activeTab: tab }),
}));

// Mirrors engine/domain/models.py

export type ContentType = 'text' | 'image' | 'video';

export interface ContentItem {
  type: ContentType;
  value: string; // text content or file path
  sort_order: number;
  category: string;
}

export interface Task {
  id: string;
  group: string;
  datetime: string; // "YYYY-MM-DD HH:MM"
  active: boolean;
  contents: ContentItem[];
  created_at: string;
  updated_at: string;
}

export interface WindowRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface AttachmentInfo {
  name: string;
  path: string;
  type: 'image' | 'video' | 'other';
  size: number;
}

export interface AttachmentStats {
  total_count: number;
  total_size_mb: number;
  referenced_count: number;
  unreferenced_count: number;
}

export interface BatchSlot {
  time: string; // "HH:MM"
  date: string; // "YYYY-MM-DD"
  contents: ContentItem[];
}

// WebSocket JSON-RPC types
export interface JsonRpcRequest {
  id: number;
  method: string;
  params: Record<string, unknown>;
}

export interface JsonRpcResponse {
  id: number;
  result?: unknown;
  error?: { code: number; message: string };
}

export interface ServerEvent {
  event: string;
  data: Record<string, unknown>;
}

export type LogLevel = 'info' | 'warn' | 'error' | 'success' | 'debug';

export interface LogEntry {
  id: number;
  level: LogLevel;
  message: string;
  timestamp: string;
}

export type EngineStatus = 'ready' | 'error' | 'not_found' | 'minimized';

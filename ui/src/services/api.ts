import type { JsonRpcRequest, ServerEvent } from '../types/models';

type MessageHandler = (event: ServerEvent) => void;

class ApiClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reqId = 0;
  private pending: Map<number, { resolve: (v: unknown) => void; reject: (e: Error) => void }> = new Map();
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _connected = false;

  constructor(url = 'ws://localhost:8765') {
    this.url = url;
  }

  get connected() { return this._connected; }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    try {
      this.ws = new WebSocket(this.url);
      this.ws.onopen = () => {
        this._connected = true;
        this.emit('connection', { connected: true });
      };
      this.ws.onclose = () => {
        this._connected = false;
        this.pending.forEach(({ reject }) => reject(new Error('Connection closed')));
        this.pending.clear();
        this.emit('connection', { connected: false });
        this.scheduleReconnect();
      };
      this.ws.onerror = () => { this.ws?.close(); };
      this.ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          if ('event' in data) {
            this.emit(data.event, data.data);
            return;
          }
          if ('id' in data) {
            const p = this.pending.get(data.id);
            if (p) {
              this.pending.delete(data.id);
              if (data.error) p.reject(new Error(data.error.message || 'RPC error'));
              else p.resolve(data.result);
            }
          }
        } catch { /* ignore malformed */ }
      };
    } catch { this.scheduleReconnect(); }
  }

  disconnect(): void {
    if (this.reconnectTimer) { clearTimeout(this.reconnectTimer); this.reconnectTimer = null; }
    if (this.ws) { this.ws.close(); this.ws = null; }
    this._connected = false;
  }

  async call(method: string, params: Record<string, unknown> = {}): Promise<unknown> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('Not connected');
    }
    const id = ++this.reqId;
    const req: JsonRpcRequest = { id, method, params };
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws!.send(JSON.stringify(req));
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`Timeout: ${method}`));
        }
      }, 15000);
    });
  }

  on(event: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(event)) this.handlers.set(event, new Set());
    this.handlers.get(event)!.add(handler);
    return () => { this.handlers.get(event)?.delete(handler); };
  }

  private emit(event: string, data: Record<string, unknown>): void {
    this.handlers.get(event)?.forEach(h => h({ event, data }));
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, 3000);
  }
}

export const apiClient = new ApiClient();

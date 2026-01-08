/**
 * WebSocket Client with automatic reconnection
 */

import type { WSMessage } from '../../types';

type MessageHandler = (message: WSMessage) => void;
type ConnectionHandler = () => void;
type ErrorHandler = (error: Event | Error) => void;

interface WebSocketClientOptions {
  url: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  pingInterval?: number;
  onMessage?: MessageHandler;
  onConnect?: ConnectionHandler;
  onDisconnect?: ConnectionHandler;
  onError?: ErrorHandler;
}

export class WebSocketClient {
  private url: string;
  private ws: WebSocket | null = null;
  private reconnectInterval: number;
  private maxReconnectAttempts: number;
  private pingInterval: number;
  private reconnectAttempts = 0;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private pingTimeout: ReturnType<typeof setTimeout> | null = null;
  private isManualClose = false;
  private messageHandlers: Set<MessageHandler> = new Set();
  private connectHandlers: Set<ConnectionHandler> = new Set();
  private disconnectHandlers: Set<ConnectionHandler> = new Set();
  private errorHandlers: Set<ErrorHandler> = new Set();
  private subscribedJobs: Set<string> = new Set();

  constructor(options: WebSocketClientOptions) {
    this.url = options.url;
    this.reconnectInterval = options.reconnectInterval ?? 3000;
    this.maxReconnectAttempts = options.maxReconnectAttempts ?? 10;
    this.pingInterval = options.pingInterval ?? 30000;

    if (options.onMessage) this.messageHandlers.add(options.onMessage);
    if (options.onConnect) this.connectHandlers.add(options.onConnect);
    if (options.onDisconnect) this.disconnectHandlers.add(options.onDisconnect);
    if (options.onError) this.errorHandlers.add(options.onError);
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isManualClose = false;
    this.createConnection();
  }

  disconnect(): void {
    this.isManualClose = true;
    this.cleanup();
    this.ws?.close(1000, 'Manual disconnect');
    this.ws = null;
  }

  private createConnection(): void {
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);
    } catch (error) {
      console.error('WebSocket connection error:', error);
      this.scheduleReconnect();
    }
  }

  private handleOpen(): void {
    console.log('WebSocket connected');
    this.reconnectAttempts = 0;
    this.startPing();

    // Re-subscribe to jobs
    for (const jobId of this.subscribedJobs) {
      this.send({ action: 'subscribe', job_id: jobId });
    }

    // Notify handlers
    for (const handler of this.connectHandlers) {
      try {
        handler();
      } catch (error) {
        console.error('Connect handler error:', error);
      }
    }
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WSMessage = JSON.parse(event.data);

      // Handle pong internally
      if (message.type === 'pong') {
        return;
      }

      // Notify handlers
      for (const handler of this.messageHandlers) {
        try {
          handler(message);
        } catch (error) {
          console.error('Message handler error:', error);
        }
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  private handleClose(event: CloseEvent): void {
    console.log('WebSocket closed:', event.code, event.reason);
    this.cleanup();

    // Notify handlers
    for (const handler of this.disconnectHandlers) {
      try {
        handler();
      } catch (error) {
        console.error('Disconnect handler error:', error);
      }
    }

    // Reconnect if not manual close
    if (!this.isManualClose) {
      this.scheduleReconnect();
    }
  }

  private handleError(event: Event): void {
    console.error('WebSocket error:', event);

    // Notify handlers
    for (const handler of this.errorHandlers) {
      try {
        handler(event);
      } catch (error) {
        console.error('Error handler error:', error);
      }
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnect attempts reached');
      return;
    }

    const delay = this.reconnectInterval * Math.pow(1.5, this.reconnectAttempts);
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1})`);

    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++;
      this.createConnection();
    }, delay);
  }

  private startPing(): void {
    this.stopPing();
    this.pingTimeout = setInterval(() => {
      if (this.isConnected) {
        this.send({ action: 'ping' });
      }
    }, this.pingInterval);
  }

  private stopPing(): void {
    if (this.pingTimeout) {
      clearInterval(this.pingTimeout);
      this.pingTimeout = null;
    }
  }

  private cleanup(): void {
    this.stopPing();
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  send(data: Record<string, unknown>): boolean {
    if (!this.isConnected) {
      console.warn('WebSocket not connected, cannot send message');
      return false;
    }

    try {
      this.ws!.send(JSON.stringify(data));
      return true;
    } catch (error) {
      console.error('Failed to send WebSocket message:', error);
      return false;
    }
  }

  // Job subscription
  subscribeToJob(jobId: string): void {
    this.subscribedJobs.add(jobId);
    if (this.isConnected) {
      this.send({ action: 'subscribe', job_id: jobId });
    }
  }

  unsubscribeFromJob(jobId: string): void {
    this.subscribedJobs.delete(jobId);
    if (this.isConnected) {
      this.send({ action: 'unsubscribe', job_id: jobId });
    }
  }

  requestQueueStatus(): void {
    this.send({ action: 'request_status' });
  }

  // Handler management
  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onConnect(handler: ConnectionHandler): () => void {
    this.connectHandlers.add(handler);
    return () => this.connectHandlers.delete(handler);
  }

  onDisconnect(handler: ConnectionHandler): () => void {
    this.disconnectHandlers.add(handler);
    return () => this.disconnectHandlers.delete(handler);
  }

  onError(handler: ErrorHandler): () => void {
    this.errorHandlers.add(handler);
    return () => this.errorHandlers.delete(handler);
  }
}

// Singleton instance
let wsClient: WebSocketClient | null = null;

// Detect if running in Tauri (check at runtime)
function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI__' in window;
}

function getWebSocketUrl(): string {
  // In Tauri, always use localhost:8000 directly
  if (isTauri()) {
    return 'ws://localhost:8000/ws/progress';
  }
  // Use environment variable if available
  if (import.meta.env.VITE_WS_BASE_URL) {
    return `${import.meta.env.VITE_WS_BASE_URL}/ws/progress`;
  }
  // Fallback to window.location for dev proxy
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/ws/progress`;
}

export function getWebSocketClient(): WebSocketClient {
  if (!wsClient) {
    wsClient = new WebSocketClient({
      url: getWebSocketUrl(),
    });
  }
  return wsClient;
}

export function initWebSocket(): WebSocketClient {
  const client = getWebSocketClient();
  client.connect();
  return client;
}

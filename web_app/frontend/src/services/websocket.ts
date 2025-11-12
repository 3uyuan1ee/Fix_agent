// WebSocket service for real-time communication

import { io, Socket } from 'socket.io-client';
import { WebSocketMessage, StreamChunk } from '../types';

export class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  connect(sessionId: string, token?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

        this.socket = io(wsUrl, {
          auth: {
            token: token,
            session_id: sessionId,
          },
          transports: ['websocket'],
        });

        this.socket.on('connect', () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          resolve();
        });

        this.socket.on('disconnect', (reason) => {
          console.log('WebSocket disconnected:', reason);
          this.handleReconnect(sessionId, token);
        });

        this.socket.on('connect_error', (error) => {
          console.error('WebSocket connection error:', error);
          reject(error);
        });

      } catch (error) {
        reject(error);
      }
    });
  }

  private handleReconnect(sessionId: string, token?: string) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

      setTimeout(() => {
        if (this.socket) {
          this.socket.connect();
        }
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  isConnected(): boolean {
    return this.socket?.connected || false;
  }

  // Event listeners
  onChunk(callback: (chunk: StreamChunk) => void) {
    if (this.socket) {
      this.socket.on('chunk', callback);
    }
  }

  onStatus(callback: (status: { type: string; message: string; metadata?: any }) => void) {
    if (this.socket) {
      this.socket.on('status', callback);
    }
  }

  onError(callback: (error: { type: string; message: string }) => void) {
    if (this.socket) {
      this.socket.on('error', callback);
    }
  }

  onMemoryList(callback: (files: string[]) => void) {
    if (this.socket) {
      this.socket.on('memory_list', callback);
    }
  }

  onMemoryContent(callback: (data: { file_path: string; content: string }) => void) {
    if (this.socket) {
      this.socket.on('memory_content', callback);
    }
  }

  onPong(callback: () => void) {
    if (this.socket) {
      this.socket.on('pong', callback);
    }
  }

  // Message senders
  sendMessage(message: WebSocketMessage) {
    if (this.socket?.connected) {
      this.socket.emit('message', message);
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }

  sendChatMessage(content: string, fileReferences?: string[]) {
    this.sendMessage({
      type: 'chat',
      content,
      file_references: fileReferences,
    });
  }

  ping() {
    this.sendMessage({ type: 'ping' });
  }

  requestMemoryList() {
    this.sendMessage({ type: 'memory_list' });
  }

  requestMemoryContent(filePath: string) {
    this.sendMessage({
      type: 'memory_read',
      file_path: filePath,
    });
  }

  writeMemoryFile(filePath: string, content: string) {
    this.sendMessage({
      type: 'memory_write',
      file_path: filePath,
      content,
    });
  }

  // Remove event listeners
  offChunk(callback: (chunk: StreamChunk) => void) {
    if (this.socket) {
      this.socket.off('chunk', callback);
    }
  }

  offStatus(callback: (status: any) => void) {
    if (this.socket) {
      this.socket.off('status', callback);
    }
  }

  offError(callback: (error: any) => void) {
    if (this.socket) {
      this.socket.off('error', callback);
    }
  }

  offMemoryList(callback: (files: string[]) => void) {
    if (this.socket) {
      this.socket.off('memory_list', callback);
    }
  }

  offMemoryContent(callback: (data: any) => void) {
    if (this.socket) {
      this.socket.off('memory_content', callback);
    }
  }

  offPong(callback: () => void) {
    if (this.socket) {
      this.socket.off('pong', callback);
    }
  }
}

// Create singleton instance
export const wsService = new WebSocketService();

// React hook for WebSocket
import { useEffect, useRef, useState } from 'react';

export const useWebSocket = (sessionId: string, token?: string) => {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    let mounted = true;

    const connect = async () => {
      try {
        await wsService.connect(sessionId, token);
        if (mounted) {
          setIsConnected(true);
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Connection failed');
          setIsConnected(false);
        }
      }
    };

    connect();

    return () => {
      mounted = false;
      wsService.disconnect();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [sessionId, token]);

  return {
    isConnected,
    error,
    reconnect: () => wsService.connect(sessionId, token),
  };
};
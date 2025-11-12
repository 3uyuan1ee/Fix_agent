// Core type definitions for the Fix Agent web application

export interface User {
  id: number;
  email: string;
  full_name?: string;
  is_active: boolean;
  created_at: string;
}

export interface Session {
  session_id: string;
  title: string;
  workspace_path: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Message {
  id: number;
  session_id: string;
  content: string;
  role: 'user' | 'assistant';
  metadata?: Record<string, any>;
  created_at: string;
}

export interface UploadedFile {
  id: number;
  filename: string;
  original_filename: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  created_at: string;
}

export interface Project {
  id: number;
  name: string;
  description?: string;
  project_path: string;
  project_type?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  analysis_count: number;
}

export interface AnalysisResult {
  analysis_id: number;
  project_id: number;
  analysis_type: string;
  file_path: string;
  status: string;
  result_data: Record<string, any>;
  created_at: string;
}

// WebSocket message types
export interface ChatMessage {
  type: 'chat';
  content: string;
  file_references?: string[];
}

export interface StreamChunk {
  type: 'message' | 'tool_call' | 'todos' | 'error' | 'status';
  content?: string;
  session_id: string;
  metadata?: Record<string, any>;
  tool?: string;
  args?: Record<string, any>;
  todos?: Array<{
    id: string;
    content: string;
    status: 'pending' | 'in_progress' | 'completed';
  }>;
}

export interface WebSocketMessage {
  type: 'chat' | 'ping' | 'memory_list' | 'memory_read' | 'memory_write';
  content?: string;
  file_path?: string;
  file_references?: string[];
}

export interface MemoryFile {
  name: string;
  path: string;
  size: number;
  modified: string;
}

// API Request/Response types
export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
}

export interface SessionCreateRequest {
  title?: string;
  workspace_path?: string;
}

export interface FileUploadResponse {
  file_id: number;
  filename: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  file_path: string;
}

export interface ConfigurationInfo {
  available_models: string[];
  default_model: string;
  available_tools: string[];
  system_info: Record<string, any>;
}

// UI State types
export interface ChatState {
  messages: Message[];
  isConnected: boolean;
  isTyping: boolean;
  currentSession?: Session;
  error?: string;
}

export interface FileExplorerState {
  files: UploadedFile[];
  currentPath: string;
  selectedFiles: string[];
  isLoading: boolean;
}

export interface MemoryState {
  files: string[];
  selectedFile?: string;
  content: string;
  isLoading: boolean;
}

// Component Props
export interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean;
}

export interface FileUploadProps {
  sessionId: string;
  onFileUploaded: (file: UploadedFile) => void;
  onError: (error: string) => void;
}

export interface SessionListProps {
  sessions: Session[];
  activeSessionId?: string;
  onSessionSelect: (session: Session) => void;
  onSessionCreate: () => void;
  onSessionDelete: (sessionId: string) => void;
}

export interface ToolCallProps {
  tool: string;
  args: Record<string, any>;
  status: 'pending' | 'running' | 'completed' | 'failed';
}

// Error types
export interface AppError {
  message: string;
  code?: string;
  details?: Record<string, any>;
}

// Configuration
export interface AppConfig {
  apiUrl: string;
  wsUrl: string;
  maxFileSize: number;
  supportedFileTypes: string[];
}
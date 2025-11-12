// API service for communicating with the backend

import axios, { AxiosResponse } from 'axios';
import {
  ApiResponse,
  Session,
  SessionCreateRequest,
  Message,
  UploadedFile,
  Project,
  AnalysisResult,
  ConfigurationInfo,
  FileUploadResponse
} from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// Create axios instance with default configuration
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth token if available
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Session API
export const sessionApi = {
  // Create new session
  createSession: async (data: SessionCreateRequest): Promise<Session> => {
    const response: AxiosResponse<ApiResponse<Session>> = await apiClient.post('/sessions', data);
    return response.data.data!;
  },

  // Get session by ID
  getSession: async (sessionId: string): Promise<Session> => {
    const response: AxiosResponse<ApiResponse<Session>> = await apiClient.get(`/sessions/${sessionId}`);
    return response.data.data!;
  },

  // Get user sessions
  getUserSessions: async (): Promise<Session[]> => {
    const response: AxiosResponse<ApiResponse<Session[]>> = await apiClient.get('/sessions');
    return response.data.data!;
  },

  // Update session title
  updateSessionTitle: async (sessionId: string, title: string): Promise<Session> => {
    const response: AxiosResponse<ApiResponse<Session>> = await apiClient.patch(`/sessions/${sessionId}`, { title });
    return response.data.data!;
  },

  // Delete session
  deleteSession: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/sessions/${sessionId}`);
  },

  // Get session messages
  getSessionMessages: async (sessionId: string, limit = 100): Promise<Message[]> => {
    const response: AxiosResponse<ApiResponse<Message[]>> = await apiClient.get(`/sessions/${sessionId}/messages?limit=${limit}`);
    return response.data.data!;
  },
};

// File API
export const fileApi = {
  // Upload file
  uploadFile: async (sessionId: string, file: File): Promise<FileUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);

    const response: AxiosResponse<ApiResponse<FileUploadResponse>> = await apiClient.post(
      '/files/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data.data!;
  },

  // List files in workspace
  listFiles: async (sessionId: string, path = ''): Promise<any[]> => {
    const response: AxiosResponse<ApiResponse<any[]>> = await apiClient.get(
      `/files/${sessionId}?path=${encodeURIComponent(path)}`
    );
    return response.data.data!;
  },

  // Get file content
  getFileContent: async (sessionId: string, filePath: string): Promise<{ content: string; file_size: number }> => {
    const response: AxiosResponse<ApiResponse<any>> = await apiClient.get(
      `/files/${sessionId}/content?path=${encodeURIComponent(filePath)}`
    );
    return response.data.data!;
  },

  // Delete file
  deleteFile: async (sessionId: string, filePath: string): Promise<void> => {
    await apiClient.delete(`/files/${sessionId}?path=${encodeURIComponent(filePath)}`);
  },
};

// Project API
export const projectApi = {
  // Create project
  createProject: async (data: any): Promise<Project> => {
    const response: AxiosResponse<ApiResponse<Project>> = await apiClient.post('/projects', data);
    return response.data.data!;
  },

  // Get user projects
  getProjects: async (): Promise<Project[]> => {
    const response: AxiosResponse<ApiResponse<Project[]>> = await apiClient.get('/projects');
    return response.data.data!;
  },

  // Get project by ID
  getProject: async (projectId: number): Promise<Project> => {
    const response: AxiosResponse<ApiResponse<Project>> = await apiClient.get(`/projects/${projectId}`);
    return response.data.data!;
  },

  // Analyze project
  analyzeProject: async (projectId: number, analysisType = 'defect_analysis'): Promise<AnalysisResult> => {
    const response: AxiosResponse<ApiResponse<AnalysisResult>> = await apiClient.post(
      `/projects/${projectId}/analyze`,
      { analysis_type: analysisType }
    );
    return response.data.data!;
  },

  // Get analysis results
  getAnalysisResults: async (projectId: number): Promise<AnalysisResult[]> => {
    const response: AxiosResponse<ApiResponse<AnalysisResult[]>> = await apiClient.get(`/projects/${projectId}/analyses`);
    return response.data.data!;
  },
};

// Memory API
export const memoryApi = {
  // Get memory files
  getMemoryFiles: async (sessionId: string): Promise<string[]> => {
    const response: AxiosResponse<ApiResponse<string[]>> = await apiClient.get(`/memory/${sessionId}/files`);
    return response.data.data!;
  },

  // Get memory file content
  getMemoryFileContent: async (sessionId: string, filePath: string): Promise<string> => {
    const response: AxiosResponse<ApiResponse<string>> = await apiClient.get(
      `/memory/${sessionId}/files/${encodeURIComponent(filePath)}`
    );
    return response.data.data!;
  },

  // Update memory file
  updateMemoryFile: async (sessionId: string, filePath: string, content: string): Promise<void> => {
    await apiClient.put(`/memory/${sessionId}/files/${encodeURIComponent(filePath)}`, { content });
  },
};

// Configuration API
export const configApi = {
  // Get app configuration
  getConfiguration: async (): Promise<ConfigurationInfo> => {
    const response: AxiosResponse<ApiResponse<ConfigurationInfo>> = await apiClient.get('/config');
    return response.data.data!;
  },

  // Health check
  healthCheck: async (): Promise<{ status: string; version: string }> => {
    const response: AxiosResponse<ApiResponse<any>> = await apiClient.get('/health');
    return response.data.data!;
  },
};

// Authentication API (if needed in future)
export const authApi = {
  login: async (email: string, password: string): Promise<{ access_token: string; token_type: string }> => {
    const response: AxiosResponse<ApiResponse<any>> = await apiClient.post('/auth/login', { email, password });
    return response.data.data!;
  },

  register: async (email: string, password: string, full_name?: string): Promise<{ access_token: string; token_type: string }> => {
    const response: AxiosResponse<ApiResponse<any>> = await apiClient.post('/auth/register', { email, password, full_name });
    return response.data.data!;
  },

  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout');
  },
};

export default apiClient;
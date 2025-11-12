// Main App component

import React, { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { motion } from 'framer-motion';

// Components
import { ChatInterface } from './components/ChatInterface';
import { SessionList } from './components/SessionList';
import { FileExplorer } from './components/FileExplorer';
import { MemoryManager } from './components/MemoryManager';
import { Header } from './components/Header';
import { LoadingScreen } from './components/LoadingScreen';

// Services
import { sessionApi, configApi } from './services/api';

// Types
import { Session, Message } from './types';

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<'chat' | 'files' | 'memory'>('chat');

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
    checkHealth();
  }, []);

  // Load sessions
  const loadSessions = async () => {
    try {
      const userSessions = await sessionApi.getUserSessions();
      setSessions(userSessions);

      // Auto-select first session if available
      if (userSessions.length > 0 && !currentSession) {
        await selectSession(userSessions[0]);
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Check API health
  const checkHealth = async () => {
    try {
      await configApi.healthCheck();
    } catch (error) {
      console.error('API health check failed:', error);
    }
  };

  // Create new session
  const createSession = async (title?: string) => {
    try {
      const newSession = await sessionApi.createSession({
        title: title || 'New Chat Session',
        workspace_path: undefined
      });

      setSessions(prev => [newSession, ...prev]);
      await selectSession(newSession);

      return newSession;
    } catch (error) {
      console.error('Failed to create session:', error);
      throw error;
    }
  };

  // Select session
  const selectSession = async (session: Session) => {
    setCurrentSession(session);
    setActiveTab('chat');

    // Load session messages
    try {
      const sessionMessages = await sessionApi.getSessionMessages(session.session_id);
      setMessages(sessionMessages.reverse()); // Show oldest first
    } catch (error) {
      console.error('Failed to load session messages:', error);
      setMessages([]);
    }
  };

  // Delete session
  const deleteSession = async (sessionId: string) => {
    try {
      await sessionApi.deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.session_id !== sessionId));

      if (currentSession?.session_id === sessionId) {
        setCurrentSession(null);
        setMessages([]);

        // Select next available session
        const remainingSessions = sessions.filter(s => s.session_id !== sessionId);
        if (remainingSessions.length > 0) {
          await selectSession(remainingSessions[0]);
        }
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
      throw error;
    }
  };

  // Update session title
  const updateSessionTitle = async (sessionId: string, title: string) => {
    try {
      const updatedSession = await sessionApi.updateSessionTitle(sessionId, title);
      setSessions(prev => prev.map(s =>
        s.session_id === sessionId ? updatedSession : s
      ));

      if (currentSession?.session_id === sessionId) {
        setCurrentSession(updatedSession);
      }
    } catch (error) {
      console.error('Failed to update session title:', error);
      throw error;
    }
  };

  // Handle new message received
  const handleMessageReceived = (message: Message) => {
    setMessages(prev => [...prev, message]);
  };

  if (isLoading) {
    return <LoadingScreen />;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="h-screen flex flex-col bg-gray-50">
          <Header
            onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
            onNewSession={() => createSession()}
          />

          <div className="flex flex-1 overflow-hidden">
            {/* Sidebar */}
            <motion.div
              initial={false}
              animate={{ width: sidebarOpen ? 320 : 0 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="bg-white border-r border-gray-200 overflow-hidden"
            >
              <div className="w-80 h-full">
                <SessionList
                  sessions={sessions}
                  activeSessionId={currentSession?.session_id}
                  onSessionSelect={selectSession}
                  onSessionCreate={() => createSession()}
                  onSessionDelete={deleteSession}
                  onSessionUpdate={updateSessionTitle}
                />
              </div>
            </motion.div>

            {/* Main content */}
            <div className="flex-1 flex flex-col">
              {currentSession ? (
                <>
                  {/* Tab navigation */}
                  <div className="bg-white border-b border-gray-200">
                    <nav className="flex space-x-8 px-6">
                      {[
                        { id: 'chat', label: 'Chat', icon: '💬' },
                        { id: 'files', label: 'Files', icon: '📁' },
                        { id: 'memory', label: 'Memory', icon: '🧠' },
                      ].map((tab) => (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id as any)}
                          className={`py-4 px-1 border-b-2 font-medium text-sm ${
                            activeTab === tab.id
                              ? 'border-blue-500 text-blue-600'
                              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                          }`}
                        >
                          <span className="mr-2">{tab.icon}</span>
                          {tab.label}
                        </button>
                      ))}
                    </nav>
                  </div>

                  {/* Tab content */}
                  <div className="flex-1 overflow-hidden">
                    <AnimatePresence mode="wait">
                      {activeTab === 'chat' && (
                        <motion.div
                          key="chat"
                          initial={{ opacity: 0, x: 20 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: -20 }}
                          className="h-full"
                        >
                          <ChatInterface
                            sessionId={currentSession.session_id}
                            initialMessages={messages}
                            onMessageReceived={handleMessageReceived}
                          />
                        </motion.div>
                      )}

                      {activeTab === 'files' && (
                        <motion.div
                          key="files"
                          initial={{ opacity: 0, x: 20 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: -20 }}
                          className="h-full"
                        >
                          <FileExplorer sessionId={currentSession.session_id} />
                        </motion.div>
                      )}

                      {activeTab === 'memory' && (
                        <motion.div
                          key="memory"
                          initial={{ opacity: 0, x: 20 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: -20 }}
                          className="h-full"
                        >
                          <MemoryManager sessionId={currentSession.session_id} />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </>
              ) : (
                // Empty state when no session selected
                <div className="flex-1 flex items-center justify-center">
                  <div className="text-center">
                    <div className="text-6xl mb-4">🤖</div>
                    <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                      Welcome to Fix Agent
                    </h2>
                    <p className="text-gray-600 mb-6">
                      Select an existing session or create a new one to get started
                    </p>
                    <button
                      onClick={() => createSession()}
                      className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                    >
                      Create New Session
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Toast notifications */}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
            },
            success: {
              duration: 3000,
              iconTheme: {
                primary: '#4aed88',
                secondary: '#fff',
              },
            },
            error: {
              duration: 5000,
              iconTheme: {
                primary: '#ef4444',
                secondary: '#fff',
              },
            },
          }}
        />
      </Router>
    </QueryClientProvider>
  );
}

export default App;
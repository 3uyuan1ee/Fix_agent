// Main chat interface component

import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Upload, Code, Brain, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Message, StreamChunk, ChatMessageProps } from '../types';
import { wsService } from '../services/websocket';
import { fileApi } from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';

interface ChatInterfaceProps {
  sessionId: string;
  initialMessages: Message[];
  onMessageReceived: (message: Message) => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  sessionId,
  initialMessages,
  onMessageReceived,
}) => {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [currentToolCall, setCurrentToolCall] = useState<string | null>(null);
  const [todos, setTodos] = useState<any[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  // WebSocket connection and event handlers
  useEffect(() => {
    let mounted = true;

    const setupWebSocket = async () => {
      try {
        // Note: In a real app, you'd get the token from auth context
        await wsService.connect(sessionId);

        if (mounted) {
          setIsConnected(true);
        }

        // Listen for streaming chunks
        wsService.onChunk((chunk: StreamChunk) => {
          if (!mounted) return;

          switch (chunk.type) {
            case 'message':
              if (chunk.content) {
                setStreamingContent(prev => prev + chunk.content);
              }
              break;

            case 'tool_call':
              if (chunk.tool) {
                setCurrentToolCall(chunk.tool);
              }
              break;

            case 'todos':
              if (chunk.todos) {
                setTodos(chunk.todos);
              }
              break;

            case 'status':
              if (chunk.metadata?.state === 'thinking') {
                setIsTyping(true);
              } else if (chunk.metadata?.state === 'complete') {
                setIsTyping(false);
                // Add complete streaming message to messages
                if (streamingContent) {
                  const newMessage: Message = {
                    id: Date.now(),
                    session_id: sessionId,
                    content: streamingContent,
                    role: 'assistant',
                    created_at: new Date().toISOString(),
                    metadata: { streamed: true, tool_calls: currentToolCall ? [currentToolCall] : [] },
                  };
                  setMessages(prev => [...prev, newMessage]);
                  onMessageReceived(newMessage);
                  setStreamingContent('');
                  setCurrentToolCall(null);
                }
              }
              break;

            case 'error':
              console.error('WebSocket error:', chunk.content);
              setIsTyping(false);
              setStreamingContent('');
              setCurrentToolCall(null);
              break;
          }
        });

        wsService.onError((error) => {
          if (mounted) {
            console.error('WebSocket error:', error);
            setIsTyping(false);
          }
        });

      } catch (error) {
        console.error('Failed to connect WebSocket:', error);
        if (mounted) {
          setIsConnected(false);
        }
      }
    };

    setupWebSocket();

    return () => {
      mounted = false;
      wsService.disconnect();
    };
  }, [sessionId]);

  // Handle file selection
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setSelectedFiles(prev => [...prev, ...files]);
  };

  // Upload files before sending message
  const uploadFiles = async (): Promise<string[]> => {
    const fileReferences: string[] = [];

    for (const file of selectedFiles) {
      try {
        const uploadedFile = await fileApi.uploadFile(sessionId, file);
        fileReferences.push(uploadedFile.file_path);
      } catch (error) {
        console.error('Failed to upload file:', error);
      }
    }

    return fileReferences;
  };

  // Send message
  const handleSendMessage = async () => {
    if (!inputValue.trim() && selectedFiles.length === 0) return;
    if (!isConnected) {
      alert('Not connected to server');
      return;
    }

    const content = inputValue.trim();
    const fileReferences = selectedFiles.length > 0 ? await uploadFiles() : [];

    // Add user message to local state
    const userMessage: Message = {
      id: Date.now(),
      session_id: sessionId,
      content,
      role: 'user',
      created_at: new Date().toISOString(),
      metadata: { file_references: fileReferences },
    };

    setMessages(prev => [...prev, userMessage]);
    onMessageReceived(userMessage);

    // Send via WebSocket
    wsService.sendChatMessage(content, fileReferences);

    // Clear inputs
    setInputValue('');
    setSelectedFiles([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Handle Enter key
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Remove selected file
  const removeSelectedFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <AnimatePresence initial={false}>
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
        </AnimatePresence>

        {/* Streaming message */}
        {isTyping && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start space-x-3"
          >
            <div className="flex-shrink-0 w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
              <Brain className="w-4 h-4 text-white" />
            </div>
            <div className="flex-1">
              <div className="bg-white rounded-lg shadow-sm p-4">
                {currentToolCall && (
                  <div className="flex items-center space-x-2 text-sm text-gray-600 mb-2">
                    <Code className="w-4 h-4" />
                    <span>Using: {currentToolCall}</span>
                  </div>
                )}
                <ReactMarkdown
                  className="prose prose-sm max-w-none"
                  components={{
                    code({ node, inline, className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || '');
                      return !inline && match ? (
                        <SyntaxHighlighter
                          style={tomorrow}
                          language={match[1]}
                          PreTag="div"
                          {...props}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      );
                    },
                  }}
                >
                  {streamingContent}
                </ReactMarkdown>
                <div className="flex items-center space-x-1 mt-2">
                  <Loader2 className="w-3 h-3 animate-spin text-blue-500" />
                  <span className="text-xs text-gray-500">AI is thinking...</span>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Connection status */}
        {!isConnected && (
          <div className="flex items-center justify-center p-4">
            <div className="flex items-center space-x-2 text-red-500">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">Disconnected</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Todos */}
      {todos.length > 0 && (
        <div className="border-t p-4 bg-yellow-50">
          <h4 className="font-medium text-yellow-800 mb-2">Tasks:</h4>
          <div className="space-y-1">
            {todos.map((todo, index) => (
              <div key={index} className="flex items-center space-x-2 text-sm">
                {todo.status === 'completed' ? (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                ) : (
                  <div className="w-4 h-4 border-2 border-gray-300 rounded-full" />
                )}
                <span className={todo.status === 'completed' ? 'line-through text-gray-500' : 'text-gray-700'}>
                  {todo.content}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t p-4 bg-white">
        {/* Selected files */}
        {selectedFiles.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {selectedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center space-x-2 bg-gray-100 rounded-lg px-3 py-1 text-sm"
              >
                <Paperclip className="w-3 h-3" />
                <span>{file.name}</span>
                <button
                  onClick={() => removeSelectedFile(index)}
                  className="text-red-500 hover:text-red-700"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-end space-x-2">
          <div className="flex-1">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message... (Shift+Enter for new line)"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={1}
              style={{ minHeight: '40px', maxHeight: '120px' }}
            />
          </div>

          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
            title="Attach files"
          >
            <Paperclip className="w-5 h-5" />
          </button>

          <button
            onClick={handleSendMessage}
            disabled={!isConnected || (!inputValue.trim() && selectedFiles.length === 0)}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            <Send className="w-4 h-4" />
            <span>Send</span>
          </button>
        </div>
      </div>
    </div>
  );
};

// Chat message component
const ChatMessage: React.FC<ChatMessageProps> = ({ message, isStreaming = false }) => {
  const isUser = message.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex items-start space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}
    >
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-green-500' : 'bg-blue-500'
        }`}
      >
        {isUser ? (
          <span className="text-white text-sm font-medium">U</span>
        ) : (
          <Brain className="w-4 h-4 text-white" />
        )}
      </div>

      <div className={`flex-1 max-w-3xl ${isUser ? 'text-right' : ''}`}>
        <div
          className={`inline-block rounded-lg shadow-sm p-4 ${
            isUser
              ? 'bg-green-100 text-green-900'
              : 'bg-white text-gray-900'
          }`}
        >
          {/* File references */}
          {message.metadata?.file_references && (
            <div className="mb-2 flex flex-wrap gap-1">
              {message.metadata.file_references.map((file: string, index: number) => (
                <span
                  key={index}
                  className="inline-flex items-center space-x-1 bg-gray-100 rounded px-2 py-1 text-xs"
                >
                  <Paperclip className="w-3 h-3" />
                  <span>{file.split('/').pop()}</span>
                </span>
              ))}
            </div>
          )}

          {/* Message content */}
          <ReactMarkdown
            className={`prose prose-sm max-w-none ${isUser ? 'prose-green' : ''}`}
            components={{
              code({ node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                  <SyntaxHighlighter
                    style={tomorrow}
                    language={match[1]}
                    PreTag="div"
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {message.content}
          </ReactMarkdown>

          {isStreaming && (
            <div className="flex items-center space-x-1 mt-2">
              <Loader2 className="w-3 h-3 animate-spin text-blue-500" />
              <span className="text-xs text-gray-500">...</span>
            </div>
          )}
        </div>

        <div className="text-xs text-gray-500 mt-1">
          {new Date(message.created_at).toLocaleTimeString()}
        </div>
      </div>
    </motion.div>
  );
};
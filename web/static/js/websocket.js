/**
 * WebSocket通信模块
 * 实现与服务器的实时通信功能
 */

// WebSocket管理器
const WebSocketManager = {
    // WebSocket实例
    ws: null,

    // 连接配置
    config: {
        url: null,
        reconnectInterval: 3000,
        maxReconnectAttempts: 10,
        heartbeatInterval: 30000,
        messageTimeout: 60000
    },

    // 连接状态
    status: {
        connected: false,
        reconnectAttempts: 0,
        lastHeartbeat: null,
        messageId: 0,
        pendingMessages: new Map()
    },

    // 事件回调
    callbacks: {
        onOpen: null,
        onMessage: null,
        onClose: null,
        onError: null,
        onStatusChange: null
    },

    // 定时器
    timers: {
        heartbeat: null,
        reconnect: null,
        messageTimeout: null
    },

    /**
     * 初始化WebSocket连接
     * @param {string} url WebSocket服务器地址
     * @param {Object} callbacks 事件回调函数
     * @param {Object} config 配置选项
     */
    init: function(url, callbacks = {}, config = {}) {
        this.config.url = url;
        this.config = { ...this.config, ...config };
        this.callbacks = { ...this.callbacks, ...callbacks };

        this.connect();
    },

    /**
     * 建立WebSocket连接
     */
    connect: function() {
        try {
            // 清理现有连接
            this.cleanup();

            // 创建WebSocket连接
            this.ws = new WebSocket(this.config.url);

            // 绑定事件监听器
            this.ws.onopen = (event) => this.handleOpen(event);
            this.ws.onmessage = (event) => this.handleMessage(event);
            this.ws.onclose = (event) => this.handleClose(event);
            this.ws.onerror = (event) => this.handleError(event);

            console.log('正在连接WebSocket服务器...');

        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.handleError(error);
        }
    },

    /**
     * 处理连接打开事件
     */
    handleOpen: function(event) {
        console.log('WebSocket连接已建立');

        this.status.connected = true;
        this.status.reconnectAttempts = 0;
        this.status.lastHeartbeat = Date.now();

        // 启动心跳检测
        this.startHeartbeat();

        // 重新发送待处理消息
        this.resendPendingMessages();

        // 触发连接回调
        if (this.callbacks.onOpen) {
            this.callbacks.onOpen(event);
        }

        this.updateStatus('connected');
    },

    /**
     * 处理消息接收事件
     */
    handleMessage: function(event) {
        try {
            const data = JSON.parse(event.data);

            // 更新心跳时间
            this.status.lastHeartbeat = Date.now();

            // 处理不同类型的消息
            switch (data.type) {
                case 'heartbeat':
                    this.handleHeartbeat(data);
                    break;
                case 'message':
                    this.handleChatMessage(data);
                    break;
                case 'stream':
                    this.handleStreamMessage(data);
                    break;
                case 'error':
                    this.handleErrorMessage(data);
                    break;
                case 'status':
                    this.handleStatusMessage(data);
                    break;
                default:
                    console.warn('未知消息类型:', data.type);
                    if (this.callbacks.onMessage) {
                        this.callbacks.onMessage(data);
                    }
            }

        } catch (error) {
            console.error('解析WebSocket消息失败:', error);
        }
    },

    /**
     * 处理连接关闭事件
     */
    handleClose: function(event) {
        console.log('WebSocket连接已关闭:', event.code, event.reason);

        this.status.connected = false;

        // 清理定时器
        this.clearTimers();

        // 触发关闭回调
        if (this.callbacks.onClose) {
            this.callbacks.onClose(event);
        }

        this.updateStatus('disconnected');

        // 自动重连
        if (!event.wasClean && this.status.reconnectAttempts < this.config.maxReconnectAttempts) {
            this.scheduleReconnect();
        }
    },

    /**
     * 处理连接错误事件
     */
    handleError: function(error) {
        console.error('WebSocket连接错误:', error);

        this.status.connected = false;

        // 触发错误回调
        if (this.callbacks.onError) {
            this.callbacks.onError(error);
        }

        this.updateStatus('error');
    },

    /**
     * 发送消息
     * @param {Object} data 消息数据
     * @param {Function} callback 发送回调
     * @returns {string} 消息ID
     */
    send: function(data, callback = null) {
        if (!this.status.connected) {
            console.warn('WebSocket未连接，无法发送消息');
            if (callback) {
                callback({ success: false, error: 'WebSocket未连接' });
            }
            return null;
        }

        // 生成消息ID
        const messageId = this.generateMessageId();
        data.id = messageId;
        data.timestamp = Date.now();

        try {
            // 发送消息
            this.ws.send(JSON.stringify(data));

            // 添加到待处理消息列表
            if (callback) {
                this.status.pendingMessages.set(messageId, {
                    data: data,
                    callback: callback,
                    timestamp: Date.now()
                });

                // 设置消息超时
                this.setMessageTimeout(messageId);
            }

            console.log('发送WebSocket消息:', messageId);
            return messageId;

        } catch (error) {
            console.error('发送WebSocket消息失败:', error);
            if (callback) {
                callback({ success: false, error: error.message });
            }
            return null;
        }
    },

    /**
     * 处理心跳消息
     */
    handleHeartbeat: function(data) {
        console.log('收到心跳消息:', data);

        // 回复心跳
        this.send({
            type: 'heartbeat',
            timestamp: Date.now()
        });
    },

    /**
     * 处理聊天消息
     */
    handleChatMessage: function(data) {
        // 处理消息确认
        if (data.id && this.status.pendingMessages.has(data.id)) {
            const pendingMessage = this.status.pendingMessages.get(data.id);
            pendingMessage.callback({ success: true, data: data });
            this.status.pendingMessages.delete(data.id);
            this.clearMessageTimeout(data.id);
        }

        // 触发消息回调
        if (this.callbacks.onMessage) {
            this.callbacks.onMessage(data);
        }
    },

    /**
     * 处理流式消息
     */
    handleStreamMessage: function(data) {
        // 流式消息不需要确认处理
        if (this.callbacks.onMessage) {
            this.callbacks.onMessage(data);
        }
    },

    /**
     * 处理错误消息
     */
    handleErrorMessage: function(data) {
        console.error('收到错误消息:', data);

        // 处理相关待处理消息
        if (data.messageId && this.status.pendingMessages.has(data.messageId)) {
            const pendingMessage = this.status.pendingMessages.get(data.messageId);
            pendingMessage.callback({ success: false, error: data.error });
            this.status.pendingMessages.delete(data.messageId);
            this.clearMessageTimeout(data.messageId);
        }

        // 触发消息回调
        if (this.callbacks.onMessage) {
            this.callbacks.onMessage(data);
        }
    },

    /**
     * 处理状态消息
     */
    handleStatusMessage: function(data) {
        console.log('收到状态消息:', data);

        // 更新内部状态
        if (data.status) {
            this.updateStatus(data.status);
        }

        // 触发消息回调
        if (this.callbacks.onMessage) {
            this.callbacks.onMessage(data);
        }
    },

    /**
     * 启动心跳检测
     */
    startHeartbeat: function() {
        this.timers.heartbeat = setInterval(() => {
            if (this.status.connected) {
                const now = Date.now();
                const timeSinceLastHeartbeat = now - this.status.lastHeartbeat;

                // 如果超过一定时间没有收到心跳，认为连接断开
                if (timeSinceLastHeartbeat > this.config.heartbeatInterval * 2) {
                    console.warn('心跳超时，重新连接...');
                    this.reconnect();
                } else {
                    // 发送心跳
                    this.send({
                        type: 'heartbeat',
                        timestamp: now
                    });
                }
            }
        }, this.config.heartbeatInterval);
    },

    /**
     * 安排重连
     */
    scheduleReconnect: function() {
        this.status.reconnectAttempts++;

        const delay = Math.min(
            this.config.reconnectInterval * Math.pow(2, this.status.reconnectAttempts - 1),
            30000 // 最大30秒
        );

        console.log(`${delay}ms后尝试第${this.status.reconnectAttempts}次重连...`);

        this.timers.reconnect = setTimeout(() => {
            this.connect();
        }, delay);

        this.updateStatus('reconnecting');
    },

    /**
     * 重新连接
     */
    reconnect: function() {
        this.cleanup();
        this.connect();
    },

    /**
     * 重新发送待处理消息
     */
    resendPendingMessages: function() {
        for (const [messageId, pendingMessage] of this.status.pendingMessages) {
            console.log('重新发送待处理消息:', messageId);

            // 更新消息时间戳
            pendingMessage.data.timestamp = Date.now();

            try {
                this.ws.send(JSON.stringify(pendingMessage.data));
                this.setMessageTimeout(messageId);
            } catch (error) {
                console.error('重新发送消息失败:', error);
                pendingMessage.callback({ success: false, error: error.message });
                this.status.pendingMessages.delete(messageId);
            }
        }
    },

    /**
     * 设置消息超时
     */
    setMessageTimeout: function(messageId) {
        this.clearMessageTimeout(messageId);

        this.timers.messageTimeout = setTimeout(() => {
            if (this.status.pendingMessages.has(messageId)) {
                const pendingMessage = this.status.pendingMessages.get(messageId);
                pendingMessage.callback({ success: false, error: '消息超时' });
                this.status.pendingMessages.delete(messageId);
            }
        }, this.config.messageTimeout);
    },

    /**
     * 清除消息超时
     */
    clearMessageTimeout: function(messageId) {
        // 这里简化处理，实际应该存储每个消息的超时定时器
    },

    /**
     * 生成消息ID
     */
    generateMessageId: function() {
        return `msg_${Date.now()}_${++this.status.messageId}`;
    },

    /**
     * 更新连接状态
     */
    updateStatus: function(status) {
        if (this.callbacks.onStatusChange) {
            this.callbacks.onStatusChange(status);
        }
    },

    /**
     * 清理定时器
     */
    clearTimers: function() {
        if (this.timers.heartbeat) {
            clearInterval(this.timers.heartbeat);
            this.timers.heartbeat = null;
        }

        if (this.timers.reconnect) {
            clearTimeout(this.timers.reconnect);
            this.timers.reconnect = null;
        }

        if (this.timers.messageTimeout) {
            clearTimeout(this.timers.messageTimeout);
            this.timers.messageTimeout = null;
        }
    },

    /**
     * 清理连接
     */
    cleanup: function() {
        this.clearTimers();

        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }

        this.status.connected = false;

        // 清理待处理消息
        for (const [messageId, pendingMessage] of this.status.pendingMessages) {
            pendingMessage.callback({ success: false, error: '连接已关闭' });
        }
        this.status.pendingMessages.clear();
    },

    /**
     * 关闭连接
     */
    close: function() {
        console.log('关闭WebSocket连接');
        this.cleanup();
        this.updateStatus('closed');
    },

    /**
     * 获取连接状态
     */
    getStatus: function() {
        return {
            connected: this.status.connected,
            reconnectAttempts: this.status.reconnectAttempts,
            pendingMessagesCount: this.status.pendingMessages.size
        };
    },

    /**
     * 检查连接是否正常
     */
    isHealthy: function() {
        return this.status.connected &&
               (Date.now() - this.status.lastHeartbeat) < (this.config.heartbeatInterval * 2);
    }
};

// 深度分析WebSocket客户端
const DeepAnalysisWebSocket = {
    wsManager: null,

    // 配置
    config: {
        wsUrl: null,
        sessionId: null,
        context: null
    },

    // 回调函数
    callbacks: {
        onConnect: null,
        onDisconnect: null,
        onMessage: null,
        onStreamMessage: null,
        onError: null,
        onStatusChange: null
    },

    /**
     * 初始化深度分析WebSocket连接
     */
    init: function(config = {}) {
        this.config = { ...this.config, ...config };

        // 构建WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/deep`;

        this.wsManager = WebSocketManager;

        // 设置回调
        const callbacks = {
            onOpen: (event) => this.handleConnect(event),
            onMessage: (data) => this.handleMessage(data),
            onClose: (event) => this.handleDisconnect(event),
            onError: (error) => this.handleError(error),
            onStatusChange: (status) => this.handleStatusChange(status)
        };

        // 初始化WebSocket连接
        this.wsManager.init(wsUrl, callbacks, {
            maxReconnectAttempts: 5,
            reconnectInterval: 2000,
            heartbeatInterval: 30000
        });
    },

    /**
     * 处理连接建立
     */
    handleConnect: function(event) {
        console.log('深度分析WebSocket连接已建立');

        // 发送初始化消息
        this.sendInitializeMessage();

        if (this.callbacks.onConnect) {
            this.callbacks.onConnect(event);
        }
    },

    /**
     * 处理消息接收
     */
    handleMessage: function(data) {
        switch (data.type) {
            case 'chat.response':
            case 'chat.stream':
                this.handleChatMessage(data);
                break;
            case 'session.created':
            case 'session.updated':
                this.handleSessionMessage(data);
                break;
            case 'context.set':
                this.handleContextMessage(data);
                break;
            case 'analysis.started':
            case 'analysis.progress':
            case 'analysis.completed':
                this.handleAnalysisMessage(data);
                break;
            default:
                console.log('收到未知类型消息:', data);
        }
    },

    /**
     * 处理聊天消息
     */
    handleChatMessage: function(data) {
        if (this.callbacks.onMessage) {
            this.callbacks.onMessage(data);
        }

        // 流式消息特殊处理
        if (data.type === 'chat.stream') {
            if (this.callbacks.onStreamMessage) {
                this.callbacks.onStreamMessage(data);
            }
        }
    },

    /**
     * 处理会话消息
     */
    handleSessionMessage: function(data) {
        console.log('会话消息:', data);

        // 更新会话ID
        if (data.sessionId) {
            this.config.sessionId = data.sessionId;
        }
    },

    /**
     * 处理上下文消息
     */
    handleContextMessage: function(data) {
        console.log('上下文消息:', data);

        // 更新上下文
        if (data.context) {
            this.config.context = data.context;
        }
    },

    /**
     * 处理分析消息
     */
    handleAnalysisMessage: function(data) {
        console.log('分析消息:', data);

        // 传递给上层回调
        if (this.callbacks.onMessage) {
            this.callbacks.onMessage(data);
        }
    },

    /**
     * 处理连接断开
     */
    handleDisconnect: function(event) {
        console.log('深度分析WebSocket连接已断开');

        if (this.callbacks.onDisconnect) {
            this.callbacks.onDisconnect(event);
        }
    },

    /**
     * 处理连接错误
     */
    handleError: function(error) {
        console.error('深度分析WebSocket连接错误:', error);

        if (this.callbacks.onError) {
            this.callbacks.onError(error);
        }
    },

    /**
     * 处理状态变化
     */
    handleStatusChange: function(status) {
        console.log('WebSocket状态变化:', status);

        if (this.callbacks.onStatusChange) {
            this.callbacks.onStatusChange(status);
        }
    },

    /**
     * 发送初始化消息
     */
    sendInitializeMessage: function() {
        this.send({
            type: 'session.initialize',
            sessionId: this.config.sessionId,
            context: this.config.context,
            timestamp: Date.now()
        });
    },

    /**
     * 发送聊天消息
     */
    sendChatMessage: function(message, options = {}) {
        return this.send({
            type: 'chat.message',
            content: message,
            sessionId: this.config.sessionId,
            context: this.config.context,
            options: options,
            timestamp: Date.now()
        });
    },

    /**
     * 设置上下文
     */
    setContext: function(context) {
        this.config.context = context;

        return this.send({
            type: 'context.set',
            context: context,
            sessionId: this.config.sessionId,
            timestamp: Date.now()
        });
    },

    /**
     * 创建新会话
     */
    createSession: function(title = null) {
        return this.send({
            type: 'session.create',
            title: title,
            timestamp: Date.now()
        });
    },

    /**
     * 发送通用消息
     */
    send: function(data, callback = null) {
        if (!this.wsManager) {
            console.error('WebSocket管理器未初始化');
            return null;
        }

        return this.wsManager.send(data, callback);
    },

    /**
     * 断开连接
     */
    disconnect: function() {
        if (this.wsManager) {
            this.wsManager.close();
        }
    },

    /**
     * 获取连接状态
     */
    getStatus: function() {
        return this.wsManager ? this.wsManager.getStatus() : null;
    },

    /**
     * 检查连接是否健康
     */
    isHealthy: function() {
        return this.wsManager ? this.wsManager.isHealthy() : false;
    },

    /**
     * 设置回调函数
     */
    setCallbacks: function(callbacks) {
        this.callbacks = { ...this.callbacks, ...callbacks };
    }
};

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        WebSocketManager,
        DeepAnalysisWebSocket
    };
} else {
    window.WebSocketManager = WebSocketManager;
    window.DeepAnalysisWebSocket = DeepAnalysisWebSocket;
}
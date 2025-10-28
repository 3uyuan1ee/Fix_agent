/**
 * 深度分析页面JavaScript逻辑
 * 实现ChatGPT风格的对话界面和交互功能
 */

// 深度分析管理器
const DeepAnalysisManager = {
    // 页面状态
    currentSessionId: null,
    sessions: [],
    messages: [],
    currentContext: null,
    isTyping: false,
    streamingMessage: null,

    // 配置选项
    config: {
        maxMessages: 100,
        autoSave: true,
        enableMarkdown: true,
        enableTypingEffect: true,
        showTimestamps: true,
        model: 'auto',
        analysisDepth: 'standard'
    },

    // DOM元素引用
    elements: {},

    // 初始化
    init: function() {
        this.cacheElements();
        this.bindEvents();
        this.loadSessions();
        this.initializeWebSocket();
        this.loadSettings();
        this.setupMarkdown();
    },

    // 缓存DOM元素
    cacheElements: function() {
        this.elements = {
            // 聊天相关
            chatMessages: document.getElementById('chatMessages'),
            chatInput: document.getElementById('chatInput'),
            sendBtn: document.getElementById('sendBtn'),
            welcomeMessage: document.getElementById('welcomeMessage'),

            // 会话相关
            sessionsList: document.getElementById('sessionsList'),
            currentSessionTitle: document.getElementById('currentSessionTitle'),
            newChatBtn: document.getElementById('newChatBtn'),
            clearSessionsBtn: document.getElementById('clearSessionsBtn'),

            // 上下文相关
            contextBtn: document.getElementById('contextBtn'),
            contextInfo: document.getElementById('contextInfo'),
            contextPath: document.getElementById('contextPath'),
            contextRemoveBtn: document.getElementById('contextRemoveBtn'),

            // 工具栏
            exportChatBtn: document.getElementById('exportChatBtn'),
            settingsBtn: document.getElementById('settingsBtn'),

            // 模态框
            contextModal: document.getElementById('contextModal'),
            settingsModal: document.getElementById('settingsModal'),
            voiceModal: document.getElementById('voiceModal'),

            // 输入相关
            charCount: document.getElementById('charCount'),
            attachFileBtn: document.getElementById('attachFileBtn'),
            voiceInputBtn: document.getElementById('voiceInputBtn'),

            // 移动端
            sidebar: document.getElementById('chatSidebar'),
            sidebarToggleBtn: document.getElementById('sidebarToggleBtn'),
            mobileSidebarToggle: document.getElementById('mobileSidebarToggle')
        };
    },

    // 绑定事件监听器
    bindEvents: function() {
        // 聊天输入事件
        this.elements.chatInput.addEventListener('input', () => this.handleInput());
        this.elements.chatInput.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.elements.sendBtn.addEventListener('click', () => this.sendMessage());

        // 会话管理事件
        this.elements.newChatBtn.addEventListener('click', () => this.createNewSession());
        this.elements.clearSessionsBtn.addEventListener('click', () => this.clearSessions());

        // 上下文管理事件
        this.elements.contextBtn.addEventListener('click', () => this.showContextModal());
        this.elements.contextRemoveBtn.addEventListener('click', () => this.removeContext());

        // 工具栏事件
        this.elements.exportChatBtn.addEventListener('click', () => this.exportChat());
        this.elements.settingsBtn.addEventListener('click', () => this.showSettingsModal());

        // 侧边栏事件
        this.elements.sidebarToggleBtn.addEventListener('click', () => this.toggleSidebar());
        this.elements.mobileSidebarToggle.addEventListener('click', () => this.toggleSidebar());

        // 建议芯片点击事件
        document.querySelectorAll('.suggestion-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const suggestion = chip.dataset.suggestion;
                if (suggestion) {
                    this.elements.chatInput.value = suggestion;
                    this.handleInput();
                    this.sendMessage();
                }
            });
        });

        // 设置保存事件
        const saveSettingsBtn = document.getElementById('saveSettingsBtn');
        if (saveSettingsBtn) {
            saveSettingsBtn.addEventListener('click', () => this.saveSettings());
        }

        // 上下文确认事件
        const confirmContextBtn = document.getElementById('confirmContextBtn');
        if (confirmContextBtn) {
            confirmContextBtn.addEventListener('click', () => this.confirmContextSelection());
        }

        // 窗口大小变化事件
        window.addEventListener('resize', () => this.handleResize());

        // 页面卸载事件
        window.addEventListener('beforeunload', () => this.handleBeforeUnload());

        // 在线/离线状态监听
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());
    },

    // 初始化WebSocket连接
    initializeWebSocket: function() {
        DeepAnalysisWebSocket.init({
            sessionId: this.currentSessionId,
            context: this.currentContext
        });

        // 设置回调
        DeepAnalysisWebSocket.setCallbacks({
            onConnect: () => this.handleWebSocketConnect(),
            onDisconnect: () => this.handleWebSocketDisconnect(),
            onMessage: (data) => this.handleWebSocketMessage(data),
            onStreamMessage: (data) => this.handleWebSocketStreamMessage(data),
            onError: (error) => this.handleWebSocketError(error),
            onStatusChange: (status) => this.handleWebSocketStatusChange(status)
        });
    },

    // 处理输入变化
    handleInput: function() {
        const input = this.elements.chatInput.value;
        const charCount = input.length;

        // 更新字符计数
        this.elements.charCount.textContent = `${charCount} / 4000`;

        // 自动调整输入框高度
        this.adjustInputHeight();

        // 更新发送按钮状态
        this.elements.sendBtn.disabled = !input.trim() || this.isTyping;

        // 隐藏欢迎消息
        if (input.trim() && this.messages.length === 0) {
            this.elements.welcomeMessage.style.display = 'none';
        }
    },

    // 处理键盘事件
    handleKeydown: function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            this.sendMessage();
        }
    },

    // 自动调整输入框高度
    adjustInputHeight: function() {
        const input = this.elements.chatInput;
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 200) + 'px';
    },

    // 发送消息
    sendMessage: async function() {
        const content = this.elements.chatInput.value.trim();
        if (!content || this.isTyping) return;

        // 隐藏欢迎消息
        this.elements.welcomeMessage.style.display = 'none';

        // 创建用户消息
        const userMessage = {
            id: this.generateMessageId(),
            type: 'user',
            content: content,
            timestamp: Date.now()
        };

        // 添加消息到列表
        this.addMessage(userMessage);
        this.messages.push(userMessage);

        // 清空输入框
        this.elements.chatInput.value = '';
        this.handleInput();

        // 显示打字状态
        this.setTypingState(true);

        try {
            // 发送消息到WebSocket
            const messageId = DeepAnalysisWebSocket.sendChatMessage(content, {
                sessionId: this.currentSessionId,
                context: this.currentContext,
                model: this.config.model,
                analysisDepth: this.config.analysisDepth
            });

            if (messageId) {
                userMessage.wsId = messageId;
            }

        } catch (error) {
            console.error('发送消息失败:', error);
            this.setTypingState(false);
            this.showErrorMessage('发送消息失败，请重试。');
        }

        // 自动保存
        if (this.config.autoSave) {
            this.saveCurrentSession();
        }
    },

    // 添加消息到界面
    addMessage: function(message) {
        const messageElement = this.createMessageElement(message);
        this.elements.chatMessages.appendChild(messageElement);

        // 滚动到底部
        this.scrollToBottom();

        // 应用打字机效果
        if (message.type === 'ai' && this.config.enableTypingEffect && message.content) {
            this.applyTypewriterEffect(messageElement.querySelector('.message-content-markdown'), message.content);
        }
    },

    // 创建消息元素
    createMessageElement: function(message) {
        const template = document.getElementById(`${message.type}MessageTemplate`);
        if (!template) return null;

        const clone = template.content.cloneNode(true);
        const messageElement = clone.querySelector('.message');

        // 设置消息ID
        messageElement.dataset.messageId = message.id;

        // 设置消息内容
        const messageText = messageElement.querySelector('.message-text, .system-text, .error-text');
        if (messageText) {
            if (this.config.enableMarkdown && message.type === 'ai') {
                messageText.innerHTML = this.renderMarkdown(message.content);
            } else {
                messageText.textContent = message.content;
            }
        }

        // 设置时间戳
        if (this.config.showTimestamps) {
            const timeElement = messageElement.querySelector('.time-text');
            if (timeElement) {
                timeElement.textContent = this.formatTime(message.timestamp);
            }
        }

        // 绑定消息操作事件
        this.bindMessageEvents(messageElement, message);

        return messageElement;
    },

    // 绑定消息操作事件
    bindMessageEvents: function(messageElement, message) {
        // 复制按钮
        const copyBtn = messageElement.querySelector('.copy-btn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => this.copyMessage(message.content));
        }

        // 编辑按钮（仅用户消息）
        const editBtn = messageElement.querySelector('.edit-btn');
        if (editBtn && message.type === 'user') {
            editBtn.addEventListener('click', () => this.editMessage(message));
        }

        // 删除按钮（仅用户消息）
        const deleteBtn = messageElement.querySelector('.delete-btn');
        if (deleteBtn && message.type === 'user') {
            deleteBtn.addEventListener('click', () => this.deleteMessage(message.id));
        }

        // 重新生成按钮（仅AI消息）
        const regenerateBtn = messageElement.querySelector('.regenerate-btn');
        if (regenerateBtn && message.type === 'ai') {
            regenerateBtn.addEventListener('click', () => this.regenerateMessage(message));
        }

        // 点赞/点踩按钮
        const likeBtn = messageElement.querySelector('.like-btn');
        const dislikeBtn = messageElement.querySelector('.dislike-btn');
        if (likeBtn) {
            likeBtn.addEventListener('click', () => this.rateMessage(message.id, 'like'));
        }
        if (dislikeBtn) {
            dislikeBtn.addEventListener('click', () => this.rateMessage(message.id, 'dislike'));
        }
    },

    // 渲染Markdown
    renderMarkdown: function(content) {
        if (!window.marked) {
            return this.escapeHtml(content);
        }

        try {
            // 配置marked选项
            marked.setOptions({
                breaks: true,
                gfm: true,
                sanitize: false,
                smartLists: true,
                smartypants: true
            });

            let html = marked.parse(content);

            // 处理代码高亮
            if (window.Prism) {
                html = html.replace(/<pre><code class="language-(\w+)">([\s\S]*?)<\/code><\/pre>/g, (match, lang, code) => {
                    const highlighted = Prism.highlight(code, Prism.languages[lang] || Prism.languages.plaintext, lang);
                    return `<pre><code class="language-${lang}">${highlighted}</code></pre>`;
                });
            }

            return html;

        } catch (error) {
            console.error('Markdown渲染失败:', error);
            return this.escapeHtml(content);
        }
    },

    // 应用打字机效果
    applyTypewriterEffect: function(element, content) {
        if (!this.config.enableTypingEffect) {
            element.innerHTML = this.renderMarkdown(content);
            return;
        }

        let index = 0;
        element.innerHTML = '';

        const typeNextChar = () => {
            if (index < content.length) {
                element.innerHTML = this.renderMarkdown(content.substring(0, index + 1));
                index++;
                this.scrollToBottom();
                setTimeout(typeNextChar, 20); // 调整打字速度
            }
        };

        typeNextChar();
    },

    // 设置打字状态
    setTypingState: function(isTyping) {
        this.isTyping = isTyping;
        this.elements.sendBtn.disabled = isTyping;

        // 更新状态指示器
        const sessionStatus = document.getElementById('sessionStatus');
        if (sessionStatus) {
            const statusText = sessionStatus.querySelector('span:last-child');
            if (statusText) {
                statusText.textContent = isTyping ? 'AI正在思考...' : '就绪';
            }
        }

        // 显示/隐藏打字指示器
        this.updateTypingIndicator(isTyping);
    },

    // 更新打字指示器
    updateTypingIndicator: function(show) {
        // 移除现有的打字指示器
        const existingIndicator = document.querySelector('.typing-indicator-message');
        if (existingIndicator) {
            existingIndicator.remove();
        }

        if (show) {
            // 创建打字指示器
            const indicator = document.createElement('div');
            indicator.className = 'message ai-message typing-indicator-message';
            indicator.innerHTML = `
                <div class="message-content">
                    <div class="message-avatar">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div class="message-body">
                        <div class="message-text">
                            <div class="typing-indicator">
                                <span></span>
                                <span></span>
                                <span></span>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            this.elements.chatMessages.appendChild(indicator);
            this.scrollToBottom();
        }
    },

    // WebSocket事件处理
    handleWebSocketConnect: function() {
        console.log('深度分析WebSocket连接已建立');
        this.updateConnectionStatus('connected');
    },

    handleWebSocketDisconnect: function() {
        console.log('深度分析WebSocket连接已断开');
        this.updateConnectionStatus('disconnected');
        this.setTypingState(false);
    },

    handleWebSocketMessage: function(data) {
        console.log('收到WebSocket消息:', data);

        switch (data.type) {
            case 'chat.response':
                this.handleChatResponse(data);
                break;
            case 'session.created':
            case 'session.updated':
                this.handleSessionUpdate(data);
                break;
            case 'error':
                this.handleErrorMessage(data);
                break;
        }
    },

    handleWebSocketStreamMessage: function(data) {
        console.log('收到流式消息:', data);
        this.handleStreamResponse(data);
    },

    handleWebSocketError: function(error) {
        console.error('WebSocket错误:', error);
        this.updateConnectionStatus('error');
        this.showErrorMessage('连接出现问题，正在尝试重新连接...');
    },

    handleWebSocketStatusChange: function(status) {
        console.log('WebSocket状态变化:', status);
        this.updateConnectionStatus(status);
    },

    // 处理聊天响应
    handleChatResponse: function(data) {
        this.setTypingState(false);

        // 移除打字指示器
        this.updateTypingIndicator(false);

        if (data.content) {
            const aiMessage = {
                id: this.generateMessageId(),
                type: 'ai',
                content: data.content,
                timestamp: Date.now(),
                model: data.model,
                sessionId: data.sessionId
            };

            this.addMessage(aiMessage);
            this.messages.push(aiMessage);

            // 更新会话ID
            if (data.sessionId) {
                this.currentSessionId = data.sessionId;
            }

            // 自动保存
            if (this.config.autoSave) {
                this.saveCurrentSession();
            }
        }
    },

    // 处理流式响应
    handleStreamResponse: function(data) {
        if (data.type === 'start') {
            // 开始流式响应
            this.streamingMessage = {
                id: this.generateMessageId(),
                type: 'ai',
                content: '',
                timestamp: Date.now()
            };

            this.setTypingState(false);
            this.updateTypingIndicator(false);

            // 创建流式消息元素
            const messageElement = this.createMessageElement(this.streamingMessage);
            this.elements.chatMessages.appendChild(messageElement);

            this.streamingMessage.element = messageElement;
            this.streamingMessage.contentElement = messageElement.querySelector('.message-content-markdown');

        } else if (data.type === 'chunk' && this.streamingMessage) {
            // 流式数据块
            this.streamingMessage.content += data.content;

            // 更新消息内容
            if (this.streamingMessage.contentElement) {
                this.streamingMessage.contentElement.innerHTML = this.renderMarkdown(this.streamingMessage.content);
                this.scrollToBottom();
            }

        } else if (data.type === 'end' && this.streamingMessage) {
            // 流式响应结束
            this.messages.push(this.streamingMessage);
            this.streamingMessage = null;

            // 自动保存
            if (this.config.autoSave) {
                this.saveCurrentSession();
            }
        }
    },

    // 处理会话更新
    handleSessionUpdate: function(data) {
        if (data.sessionId) {
            this.currentSessionId = data.sessionId;
        }

        if (data.title) {
            this.elements.currentSessionTitle.textContent = data.title;
        }

        // 重新加载会话列表
        this.loadSessions();
    },

    // 处理错误消息
    handleErrorMessage: function(data) {
        this.setTypingState(false);
        this.updateTypingIndicator(false);
        this.showErrorMessage(data.error || '发生未知错误');
    },

    // 会话管理
    createNewSession: function() {
        const sessionId = this.generateSessionId();
        this.currentSessionId = sessionId;
        this.messages = [];

        // 清空消息界面
        this.elements.chatMessages.innerHTML = '';
        this.elements.welcomeMessage.style.display = 'block';

        // 更新界面
        this.elements.currentSessionTitle.textContent = '新建会话';

        // 隐藏上下文
        this.removeContext();

        // 通过WebSocket创建会话
        DeepAnalysisWebSocket.createSession('新建会话');

        // 重新加载会话列表
        this.loadSessions();
    },

    // 加载会话列表
    loadSessions: async function() {
        try {
            const response = await fetch('/api/deep/sessions');
            const data = await response.json();

            if (data.success) {
                this.sessions = data.sessions || [];
                this.renderSessionsList();
            }
        } catch (error) {
            console.error('加载会话列表失败:', error);
        }
    },

    // 渲染会话列表
    renderSessionsList: function() {
        if (this.sessions.length === 0) {
            this.elements.sessionsList.innerHTML = `
                <div class="no-sessions">
                    <i class="fas fa-comments me-2"></i>
                    暂无会话记录
                </div>
            `;
            return;
        }

        const sessionsHtml = this.sessions.map(session => `
            <div class="session-item ${session.id === this.currentSessionId ? 'active' : ''}"
                 data-session-id="${session.id}">
                <div class="session-title">${session.title}</div>
                <div class="session-preview">${session.lastMessage || '暂无消息'}</div>
                <div class="session-time">${this.formatTime(session.updatedAt)}</div>
            </div>
        `).join('');

        this.elements.sessionsList.innerHTML = sessionsHtml;

        // 绑定会话点击事件
        this.elements.sessionsList.querySelectorAll('.session-item').forEach(item => {
            item.addEventListener('click', () => {
                const sessionId = item.dataset.sessionId;
                this.loadSession(sessionId);
            });
        });
    },

    // 加载会话
    loadSession: async function(sessionId) {
        try {
            const response = await fetch(`/api/deep/sessions/${sessionId}`);
            const data = await response.json();

            if (data.success) {
                this.currentSessionId = sessionId;
                this.messages = data.messages || [];

                // 更新界面
                this.elements.currentSessionTitle.textContent = data.session.title;
                this.elements.welcomeMessage.style.display = 'none';

                // 渲染消息
                this.renderMessages();

                // 更新会话列表高亮
                this.updateSessionsHighlight();

                // 设置上下文
                if (data.session.context) {
                    this.currentContext = data.session.context;
                    this.updateContextDisplay();
                }
            }
        } catch (error) {
            console.error('加载会话失败:', error);
            this.showErrorMessage('加载会话失败');
        }
    },

    // 渲染消息列表
    renderMessages: function() {
        this.elements.chatMessages.innerHTML = '';

        this.messages.forEach(message => {
            const messageElement = this.createMessageElement(message);
            if (messageElement) {
                this.elements.chatMessages.appendChild(messageElement);
            }
        });

        this.scrollToBottom();
    },

    // 保存当前会话
    saveCurrentSession: async function() {
        if (!this.currentSessionId || this.messages.length === 0) return;

        try {
            await fetch('/api/deep/sessions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    sessionId: this.currentSessionId,
                    title: this.elements.currentSessionTitle.textContent,
                    messages: this.messages,
                    context: this.currentContext
                })
            });
        } catch (error) {
            console.error('保存会话失败:', error);
        }
    },

    // 清空会话列表
    clearSessions: async function() {
        if (!confirm('确定要清空所有会话记录吗？此操作无法撤销。')) return;

        try {
            const response = await fetch('/api/deep/sessions', {
                method: 'DELETE'
            });

            const data = await response.json();
            if (data.success) {
                this.sessions = [];
                this.renderSessionsList();
                this.createNewSession();
            }
        } catch (error) {
            console.error('清空会话失败:', error);
            this.showErrorMessage('清空会话失败');
        }
    },

    // 上下文管理
    showContextModal: function() {
        const modal = new bootstrap.Modal(this.elements.contextModal);
        modal.show();
        this.loadAvailableProjects();
    },

    loadAvailableProjects: async function() {
        try {
            // 加载已上传的项目
            const response = await fetch('/api/projects');
            const data = await response.json();

            if (data.success) {
                this.renderProjectsList(data.projects || []);
            }
        } catch (error) {
            console.error('加载项目列表失败:', error);
        }
    },

    renderProjectsList: function(projects) {
        const uploadedProjectsList = document.getElementById('uploadedProjectsList');
        if (!uploadedProjectsList) return;

        if (projects.length === 0) {
            uploadedProjectsList.innerHTML = `
                <div class="no-projects">
                    <i class="fas fa-folder-open me-2"></i>
                    暂无已上传的项目
                </div>
            `;
            return;
        }

        const projectsHtml = projects.map(project => `
            <div class="project-item" data-project-id="${project.id}">
                <div class="project-info">
                    <i class="fas fa-folder me-2"></i>
                    <div class="project-details">
                        <div class="project-name">${project.name}</div>
                        <div class="project-path">${project.path}</div>
                    </div>
                </div>
                <div class="project-actions">
                    <button class="btn btn-sm btn-outline-primary select-project-btn">
                        选择
                    </button>
                </div>
            </div>
        `).join('');

        uploadedProjectsList.innerHTML = projectsHtml;

        // 绑定项目选择事件
        uploadedProjectsList.querySelectorAll('.select-project-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const projectItem = e.target.closest('.project-item');
                const projectId = projectItem.dataset.projectId;
                const project = projects.find(p => p.id === projectId);
                if (project) {
                    this.selectProject(project);
                }
            });
        });
    },

    selectProject: function(project) {
        this.selectedProject = project;
        const confirmBtn = document.getElementById('confirmContextBtn');
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.textContent = `确认选择: ${project.name}`;
        }
    },

    confirmContextSelection: function() {
        if (this.selectedProject) {
            this.setContext(this.selectedProject);

            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(this.elements.contextModal);
            modal.hide();

            // 通过WebSocket设置上下文
            DeepAnalysisWebSocket.setContext(this.selectedProject);
        }
    },

    setContext: function(context) {
        this.currentContext = context;
        this.updateContextDisplay();

        // 保存到当前会话
        if (this.config.autoSave) {
            this.saveCurrentSession();
        }
    },

    updateContextDisplay: function() {
        if (this.currentContext) {
            this.elements.contextInfo.style.display = 'block';
            this.elements.contextPath.textContent = this.currentContext.path || this.currentContext.name;
        } else {
            this.elements.contextInfo.style.display = 'none';
        }
    },

    removeContext: function() {
        this.currentContext = null;
        this.updateContextDisplay();

        // 通过WebSocket清除上下文
        DeepAnalysisWebSocket.setContext(null);

        // 保存到当前会话
        if (this.config.autoSave) {
            this.saveCurrentSession();
        }
    },

    // 工具函数
    generateMessageId: function() {
        return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    },

    generateSessionId: function() {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    },

    formatTime: function(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) { // 1分钟内
            return '刚刚';
        } else if (diff < 3600000) { // 1小时内
            return `${Math.floor(diff / 60000)}分钟前`;
        } else if (diff < 86400000) { // 1天内
            return `${Math.floor(diff / 3600000)}小时前`;
        } else {
            return date.toLocaleDateString('zh-CN');
        }
    },

    escapeHtml: function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    scrollToBottom: function() {
        this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
    },

    copyMessage: function(content) {
        navigator.clipboard.writeText(content).then(() => {
            App.showAlert('消息已复制到剪贴板', 'success');
        }).catch(() => {
            App.showAlert('复制失败', 'error');
        });
    },

    editMessage: function(message) {
        const newContent = prompt('编辑消息:', message.content);
        if (newContent && newContent !== message.content) {
            message.content = newContent;
            message.timestamp = Date.now();
            this.renderMessages();
            this.saveCurrentSession();
        }
    },

    deleteMessage: function(messageId) {
        if (confirm('确定要删除这条消息吗？')) {
            this.messages = this.messages.filter(m => m.id !== messageId);
            this.renderMessages();
            this.saveCurrentSession();
        }
    },

    regenerateMessage: function(message) {
        // 找到用户消息并重新发送
        const userMessageIndex = this.messages.findIndex(m =>
            m.type === 'user' && m.timestamp < message.timestamp
        );

        if (userMessageIndex !== -1) {
            const userMessage = this.messages[userMessageIndex];
            // 删除AI消息
            this.messages = this.messages.filter(m => m.id !== message.id);
            this.renderMessages();
            // 重新发送用户消息
            this.elements.chatInput.value = userMessage.content;
            this.sendMessage();
        }
    },

    rateMessage: function(messageId, rating) {
        console.log(`消息 ${messageId} 被评为 ${rating}`);
        // 这里可以发送评分到服务器
    },

    showErrorMessage: function(message) {
        const errorElement = document.createElement('div');
        errorElement.className = 'alert alert-danger alert-dismissible fade show';
        errorElement.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        this.elements.chatMessages.appendChild(errorElement);
        this.scrollToBottom();

        // 3秒后自动消失
        setTimeout(() => {
            errorElement.remove();
        }, 3000);
    },

    updateConnectionStatus: function(status) {
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('#sessionStatus span:last-child');

        if (statusDot && statusText) {
            switch (status) {
                case 'connected':
                    statusDot.style.backgroundColor = '#10a37f';
                    statusText.textContent = '已连接';
                    break;
                case 'disconnected':
                    statusDot.style.backgroundColor = '#dc3545';
                    statusText.textContent = '已断开';
                    break;
                case 'connecting':
                case 'reconnecting':
                    statusDot.style.backgroundColor = '#ffc107';
                    statusText.textContent = '连接中...';
                    break;
                case 'error':
                    statusDot.style.backgroundColor = '#dc3545';
                    statusText.textContent = '连接错误';
                    break;
                default:
                    statusDot.style.backgroundColor = '#666';
                    statusText.textContent = '未知状态';
            }
        }
    },

    updateSessionsHighlight: function() {
        this.elements.sessionsList.querySelectorAll('.session-item').forEach(item => {
            const sessionId = item.dataset.sessionId;
            if (sessionId === this.currentSessionId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    },

    toggleSidebar: function() {
        this.elements.sidebar.classList.toggle('open');
    },

    handleResize: function() {
        // 响应式处理
        if (window.innerWidth > 768) {
            this.elements.sidebar.classList.remove('open');
        }
    },

    handleBeforeUnload: function() {
        if (this.config.autoSave) {
            this.saveCurrentSession();
        }
    },

    handleOnline: function() {
        this.updateConnectionStatus('connected');
        this.showErrorMessage('网络连接已恢复');
    },

    handleOffline: function() {
        this.updateConnectionStatus('disconnected');
        this.showErrorMessage('网络连接已断开');
    },

    // 设置相关
    showSettingsModal: function() {
        const modal = new bootstrap.Modal(this.elements.settingsModal);
        modal.show();
        this.loadSettingsToModal();
    },

    loadSettings: function() {
        const saved = localStorage.getItem('deepAnalysisSettings');
        if (saved) {
            this.config = { ...this.config, ...JSON.parse(saved) };
        }
    },

    loadSettingsToModal: function() {
        const analysisModel = document.getElementById('analysisModel');
        const analysisDepth = document.getElementById('analysisDepth');
        const maxTokens = document.getElementById('maxTokens');
        const showTimestamps = document.getElementById('showTimestamps');
        const enableMarkdown = document.getElementById('enableMarkdown');
        const enableTypingEffect = document.getElementById('enableTypingEffect');

        if (analysisModel) analysisModel.value = this.config.model;
        if (analysisDepth) analysisDepth.value = this.config.analysisDepth;
        if (maxTokens) maxTokens.value = this.config.maxTokens;
        if (showTimestamps) showTimestamps.checked = this.config.showTimestamps;
        if (enableMarkdown) enableMarkdown.checked = this.config.enableMarkdown;
        if (enableTypingEffect) enableTypingEffect.checked = this.config.enableTypingEffect;
    },

    saveSettings: function() {
        const analysisModel = document.getElementById('analysisModel');
        const analysisDepth = document.getElementById('analysisDepth');
        const maxTokens = document.getElementById('maxTokens');
        const showTimestamps = document.getElementById('showTimestamps');
        const enableMarkdown = document.getElementById('enableMarkdown');
        const enableTypingEffect = document.getElementById('enableTypingEffect');

        this.config = {
            ...this.config,
            model: analysisModel ? analysisModel.value : this.config.model,
            analysisDepth: analysisDepth ? analysisDepth.value : this.config.analysisDepth,
            maxTokens: maxTokens ? parseInt(maxTokens.value) : this.config.maxTokens,
            showTimestamps: showTimestamps ? showTimestamps.checked : this.config.showTimestamps,
            enableMarkdown: enableMarkdown ? enableMarkdown.checked : this.config.enableMarkdown,
            enableTypingEffect: enableTypingEffect ? enableTypingEffect.checked : this.config.enableTypingEffect
        };

        localStorage.setItem('deepAnalysisSettings', JSON.stringify(this.config));

        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(this.elements.settingsModal);
        modal.hide();

        App.showAlert('设置已保存', 'success');
    },

    exportChat: function() {
        if (this.messages.length === 0) {
            App.showAlert('没有可导出的消息', 'warning');
            return;
        }

        const exportData = {
            sessionId: this.currentSessionId,
            title: this.elements.currentSessionTitle.textContent,
            messages: this.messages,
            context: this.currentContext,
            exportedAt: new Date().toISOString()
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], {
            type: 'application/json'
        });

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `deep_analysis_chat_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        App.showAlert('聊天记录已导出', 'success');
    },

    setupMarkdown: function() {
        // 如果marked库不存在，创建简单的Markdown渲染器
        if (!window.marked) {
            window.marked = {
                parse: function(text) {
                    return text
                        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
                        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
                        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
                        .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
                        .replace(/\*(.*)\*/gim, '<em>$1</em>')
                        .replace(/`(.*)`/gim, '<code>$1</code>')
                        .replace(/\n\n/gim, '</p><p>')
                        .replace(/\n/gim, '<br>');
                }
            };
        }
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 设置当前页面
    App.Sidebar.setActive('deep');

    // 初始化深度分析管理器
    DeepAnalysisManager.init();
});
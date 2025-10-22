/**
 * AIDefectDetector 通用JavaScript工具库
 * 提供页面间通用的功能和工具函数
 */

// 全局变量
window.App = {
    currentPage: 'index',
    sidebarVisible: true,
    config: {},
    themes: {
        primary: '#0d6efd',
        secondary: '#6c757d',
        success: '#198754',
        danger: '#dc3545',
        warning: '#ffc107',
        info: '#0dcaf0'
    }
};

// 兼容旧版本
window.AIDefectDetector = {
    config: {
        apiBaseUrl: '/api',
        version: '1.0.0'
    },
    state: {
        isAnalyzing: false,
        currentAnalysis: null
    }
};

/**
 * AJAX请求封装函数
 * @param {string} url - 请求URL
 * @param {Object} options - 请求选项
 * @returns {Promise} 返回Promise对象
 */
App.ajax = function(url, options = {}) {
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        timeout: 30000
    };

    const finalOptions = { ...defaultOptions, ...options };

    return new Promise((resolve, reject) => {
        const timeoutId = setTimeout(() => {
            reject(new Error('请求超时'));
        }, finalOptions.timeout);

        fetch(url, finalOptions)
            .then(response => {
                clearTimeout(timeoutId);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                resolve(data);
            })
            .catch(error => {
                clearTimeout(timeoutId);
                reject(error);
            });
    });
};

/**
 * GET请求快捷方法
 */
App.get = function(url, options = {}) {
    return App.ajax(url, { ...options, method: 'GET' });
};

/**
 * POST请求快捷方法
 */
App.post = function(url, data, options = {}) {
    return App.ajax(url, {
        ...options,
        method: 'POST',
        body: JSON.stringify(data)
    });
};

/**
 * 错误处理函数
 * @param {Error} error - 错误对象
 * @param {string} context - 错误上下文
 */
App.handleError = function(error, context = '') {
    console.error(`[${context}] 错误:`, error);

    let message = '操作失败';

    if (error.message.includes('超时')) {
        message = '请求超时，请检查网络连接';
    } else if (error.message.includes('HTTP 4')) {
        message = '请求参数错误';
    } else if (error.message.includes('HTTP 5')) {
        message = '服务器内部错误';
    } else if (error.message.includes('Failed to fetch')) {
        message = '网络连接失败，请检查网络';
    } else {
        message = error.message || '未知错误';
    }

    App.showAlert(message, 'danger');
};

/**
 * 显示提示信息
 * @param {string} message - 提示信息
 * @param {string} type - 提示类型 (success, danger, warning, info)
 * @param {number} duration - 显示时长（毫秒）
 */
App.showAlert = function(message, type = 'info', duration = 5000) {
    // 创建提示框容器
    const alertContainer = document.getElementById('alert-container') || (() => {
        const container = document.createElement('div');
        container.id = 'alert-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
        `;
        document.body.appendChild(container);
        return container;
    })();

    // 创建提示框
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.style.cssText = `
        margin-bottom: 10px;
        box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
        border-radius: 0.5rem;
        animation: slideInRight 0.3s ease-out;
    `;

    // 设置图标
    const icons = {
        success: 'fas fa-check-circle',
        danger: 'fas fa-times-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };

    alertDiv.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="${icons[type]} me-2"></i>
            <div class="flex-grow-1">${message}</div>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    // 添加到容器
    alertContainer.appendChild(alertDiv);

    // 绑定关闭事件
    alertDiv.querySelector('.btn-close').addEventListener('click', () => {
        alertDiv.remove();
    });

    // 自动移除
    if (duration > 0) {
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.style.animation = 'slideOutRight 0.3s ease-out';
                setTimeout(() => alertDiv.remove(), 300);
            }
        }, duration);
    }
};

/**
 * 页面状态管理
 */
App.PageState = {
    set: function(key, value) {
        try {
            sessionStorage.setItem(`app_${key}`, JSON.stringify(value));
        } catch (e) {
            console.warn('无法保存状态到sessionStorage:', e);
        }
    },

    get: function(key, defaultValue = null) {
        try {
            const value = sessionStorage.getItem(`app_${key}`);
            return value ? JSON.parse(value) : defaultValue;
        } catch (e) {
            console.warn('无法从sessionStorage读取状态:', e);
            return defaultValue;
        }
    },

    remove: function(key) {
        try {
            sessionStorage.removeItem(`app_${key}`);
        } catch (e) {
            console.warn('无法从sessionStorage删除状态:', e);
        }
    }
};

/**
 * 侧边栏控制
 */
App.Sidebar = {
    show: function() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.add('show');
            App.sidebarVisible = true;
            App.PageState.set('sidebarVisible', true);
        }
    },

    hide: function() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.remove('show');
            App.sidebarVisible = false;
            App.PageState.set('sidebarVisible', false);
        }
    },

    toggle: function() {
        if (App.sidebarVisible) {
            this.hide();
        } else {
            this.show();
        }
    },

    setActive: function(pageName) {
        // 移除所有活动状态
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });

        // 设置当前页面为活动状态
        const activeLink = document.querySelector(`[data-page="${pageName}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }

        // 更新当前页面状态
        App.currentPage = pageName;
        App.PageState.set('currentPage', pageName);
    }
};

/**
 * 工具函数 - 防抖
 * @param {Function} func - 要防抖的函数
 * @param {number} wait - 等待时间（毫秒）
 * @returns {Function} 防抖后的函数
 */
App.debounce = function(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

/**
 * 工具函数 - 节流
 * @param {Function} func - 要节流的函数
 * @param {number} limit - 限制间隔（毫秒）
 * @returns {Function} 节流后的函数
 */
App.throttle = function(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
};

/**
 * 初始化应用
 */
App.init = function() {
    // 恢复页面状态
    const savedPage = App.PageState.get('currentPage') || 'index';
    const sidebarVisible = App.PageState.get('sidebarVisible', true);

    // 设置侧边栏状态
    if (window.innerWidth <= 767 && !sidebarVisible) {
        App.Sidebar.hide();
    }

    // 设置当前页面
    App.Sidebar.setActive(savedPage);

    // 绑定事件监听器
    this.bindEvents();

    console.log('AIDefectDetector 应用初始化完成');
};

/**
 * 绑定全局事件监听器
 */
App.bindEvents = function() {
    // 侧边栏切换
    const sidebarToggle = document.getElementById('sidebarToggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => App.Sidebar.toggle());
    }

    const sidebarClose = document.getElementById('sidebarClose');
    if (sidebarClose) {
        sidebarClose.addEventListener('click', () => App.Sidebar.hide());
    }

    // 导航链接点击
    document.querySelectorAll('.nav-link[data-page]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = link.getAttribute('data-page');
            App.Sidebar.setActive(page);

            // 移动端自动隐藏侧边栏
            if (window.innerWidth <= 767) {
                App.Sidebar.hide();
            }
        });
    });

    // 响应式处理
    window.addEventListener('resize', App.throttle(() => {
        if (window.innerWidth > 767) {
            const sidebar = document.getElementById('sidebar');
            if (sidebar && sidebar.classList.contains('show')) {
                sidebar.classList.remove('show');
            }
        }
    }, 250));

    // 键盘快捷键
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + B 切换侧边栏
        if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
            e.preventDefault();
            App.Sidebar.toggle();
        }
    });
};

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('AIDefectDetector Web应用初始化中...');

    // 初始化应用
    App.init();

    // 初始化工具提示
    initializeTooltips();

    // 初始化页面动画
    initializeAnimations();

    // 检查系统状态
    checkSystemHealth();

    console.log('AIDefectDetector Web应用初始化完成');
});

// 初始化Bootstrap工具提示
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// 初始化页面动画
function initializeAnimations() {
    // 为卡片添加淡入动画
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.classList.add('fade-in');
        card.style.animationDelay = `${index * 0.1}s`;
    });
}

// 检查系统健康状态
function checkSystemHealth() {
    fetch('/health')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('系统健康状态:', data);
            updateSystemStatus(data);
        })
        .catch(error => {
            console.error('系统健康检查失败:', error);
            updateSystemStatus({ status: 'unhealthy' });
        });
}

// 更新系统状态显示
function updateSystemStatus(statusData) {
    const statusElements = document.querySelectorAll('.system-status');
    statusElements.forEach(element => {
        if (statusData.status === 'healthy') {
            element.innerHTML = '<span class="status-indicator online"></span>正常';
            element.className = 'badge bg-success';
        } else {
            element.innerHTML = '<span class="status-indicator offline"></span>异常';
            element.className = 'badge bg-danger';
        }
    });
}

// API调用封装
class APIClient {
    constructor(baseUrl = '/api') {
        this.baseUrl = baseUrl;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const finalOptions = { ...defaultOptions, ...options };

        try {
            const response = await fetch(url, finalOptions);

            if (!response.ok) {
                throw new Error(`API request failed: ${response.status} ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API请求失败:', error);
            throw error;
        }
    }

    // 获取系统信息
    getSystemInfo() {
        return this.request('/info');
    }

    // 开始分析
    startAnalysis(projectPath, mode, options = {}) {
        return this.request('/analysis', {
            method: 'POST',
            body: JSON.stringify({
                project_path: projectPath,
                mode: mode,
                options: options
            })
        });
    }

    // 获取分析结果
    getAnalysisResult(analysisId) {
        return this.request(`/analysis/${analysisId}`);
    }
}

// 全局API客户端
window.api = new APIClient();

// 通知系统
class NotificationManager {
    show(message, type = 'info', duration = 5000) {
        const notification = this.createNotification(message, type);
        document.body.appendChild(notification);

        // 触发动画
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);

        // 自动移除
        setTimeout(() => {
            this.hide(notification);
        }, duration);
    }

    createNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            max-width: 500px;
        `;

        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="flex-grow-1">${message}</div>
                <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
        `;

        return notification;
    }

    hide(notification) {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }
}

// 全局通知管理器
window.notifications = new NotificationManager();

// 分析管理器
class AnalysisManager {
    constructor() {
        this.currentAnalysis = null;
    }

    async startAnalysis(projectPath, mode, options = {}) {
        if (this.currentAnalysis) {
            window.notifications.show('已有分析任务正在进行中', 'warning');
            return;
        }

        try {
            window.notifications.show(`正在开始${this.getModeText(mode)}...`, 'info');

            // 设置加载状态
            this.setLoadingState(true);

            // 调用API开始分析
            const result = await window.api.startAnalysis(projectPath, mode, options);

            this.currentAnalysis = result;
            window.notifications.show('分析任务已启动', 'success');

            // 轮询分析结果
            this.pollAnalysisResult(result.id);

        } catch (error) {
            console.error('启动分析失败:', error);
            window.notifications.show('启动分析失败: ' + error.message, 'error');
            this.setLoadingState(false);
        }
    }

    async pollAnalysisResult(analysisId) {
        const maxAttempts = 60; // 最多轮询60次
        let attempts = 0;

        const poll = async () => {
            try {
                const result = await window.api.getAnalysisResult(analysisId);

                if (result.status === 'completed') {
                    this.handleAnalysisComplete(result);
                } else if (result.status === 'failed') {
                    this.handleAnalysisError(result);
                } else {
                    // 继续轮询
                    attempts++;
                    if (attempts < maxAttempts) {
                        setTimeout(poll, 2000); // 2秒后再次轮询
                    } else {
                        window.notifications.show('分析超时，请稍后查看结果', 'warning');
                        this.setLoadingState(false);
                    }
                }
            } catch (error) {
                console.error('轮询分析结果失败:', error);
                setTimeout(poll, 5000); // 5秒后重试
            }
        };

        poll();
    }

    handleAnalysisComplete(result) {
        this.setLoadingState(false);
        this.currentAnalysis = null;
        window.notifications.show('分析完成！', 'success');

        // TODO: 显示分析结果
        console.log('分析结果:', result);
    }

    handleAnalysisError(result) {
        this.setLoadingState(false);
        this.currentAnalysis = null;
        window.notifications.show('分析失败: ' + result.error, 'error');
    }

    setLoadingState(isLoading) {
        window.AIDefectDetector.state.isAnalyzing = isLoading;

        // 更新UI状态
        const buttons = document.querySelectorAll('.btn-analysis');
        buttons.forEach(button => {
            if (isLoading) {
                button.disabled = true;
                button.innerHTML = '<span class="loading me-2"></span>分析中...';
            } else {
                button.disabled = false;
                button.innerHTML = button.getAttribute('data-original-text') || '开始分析';
            }
        });
    }

    getModeText(mode) {
        const modeMap = {
            'static': '静态分析',
            'deep': '深度分析',
            'fix': '分析修复'
        };
        return modeMap[mode] || mode;
    }
}

// 全局分析管理器
window.analysisManager = new AnalysisManager();

// 工具函数
window.utils = {
    // 格式化文件大小
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // 格式化时间
    formatTime(timestamp) {
        return new Date(timestamp * 1000).toLocaleString();
    },

    // 获取文件扩展名
    getFileExtension(filename) {
        return filename.slice((filename.lastIndexOf(".") - 1 >>> 0) + 2);
    },

    // 防抖函数
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// 导出模块（如果使用模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        APIClient,
        NotificationManager,
        AnalysisManager,
        utils: window.utils
    };
}
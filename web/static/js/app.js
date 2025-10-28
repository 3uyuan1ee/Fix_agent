/**
 * AIDefectDetector 通用JavaScript工具库
 * 提供页面间通用的功能和工具函数
 */

// 全局变量
window.App = {
    currentPage: 'index',
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
        const xhr = new XMLHttpRequest();
        xhr.open(finalOptions.method, url, true);

        // 设置请求头
        Object.keys(finalOptions.headers).forEach(key => {
            xhr.setRequestHeader(key, finalOptions.headers[key]);
        });

        // 设置超时
        xhr.timeout = finalOptions.timeout;

        xhr.onload = function() {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const response = xhr.getResponseHeader('Content-Type').includes('application/json')
                        ? JSON.parse(xhr.responseText)
                        : xhr.responseText;
                    resolve(response);
                } catch (e) {
                    resolve(xhr.responseText);
                }
            } else {
                reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
            }
        };

        xhr.onerror = function() {
            reject(new Error('网络请求失败'));
        };

        xhr.ontimeout = function() {
            reject(new Error('请求超时'));
        };

        // 发送请求
        const data = finalOptions.data;
        if (data) {
            if (typeof data === 'object' && finalOptions.headers['Content-Type'].includes('application/json')) {
                xhr.send(JSON.stringify(data));
            } else {
                xhr.send(data);
            }
        } else {
            xhr.send();
        }
    });
};

/**
 * 显示通知消息
 * @param {string} message - 消息内容
 * @param {string} type - 消息类型 (success, info, warning, danger)
 * @param {Object} options - 选项
 */
App.notify = function(message, type = 'info', options = {}) {
    const defaultOptions = {
        duration: 5000,
        dismissible: true
    };

    const finalOptions = { ...defaultOptions, ...options };

    // 创建通知元素
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';

    alertDiv.innerHTML = `
        ${message}
        ${finalOptions.dismissible ? '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' : ''}
    `;

    // 添加到页面
    document.body.appendChild(alertDiv);

    // 自动移除
    if (finalOptions.duration > 0) {
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.parentNode.removeChild(alertDiv);
            }
        }, finalOptions.duration);
    }

    return alertDiv;
};

/**
 * 显示加载指示器
 * @param {string} message - 加载消息
 * @returns {Object} 加载器对象
 */
App.showLoading = function(message = '加载中...') {
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
    overlay.style.cssText = 'background-color: rgba(0,0,0,0.5); z-index: 9999;';

    overlay.innerHTML = `
        <div class="bg-white p-4 rounded shadow-lg text-center">
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <div>${message}</div>
        </div>
    `;

    document.body.appendChild(overlay);

    return {
        hide: () => {
            if (overlay.parentNode) {
                overlay.parentNode.removeChild(overlay);
            }
        },
        updateMessage: (newMessage) => {
            const messageDiv = overlay.querySelector('.bg-white div:last-child');
            if (messageDiv) {
                messageDiv.textContent = newMessage;
            }
        }
    };
};

/**
 * 确认对话框
 * @param {string} message - 确认消息
 * @param {string} title - 对话框标题
 * @returns {Promise} 返回Promise对象
 */
App.confirm = function(message, title = '确认') {
    return new Promise((resolve) => {
        if (window.confirm(`${title}\n\n${message}`)) {
            resolve(true);
        } else {
            resolve(false);
        }
    });
};

/**
 * 格式化文件大小
 * @param {number} bytes - 字节数
 * @returns {string} 格式化后的文件大小
 */
App.formatFileSize = function(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * 格式化时间
 * @param {Date|string} date - 日期对象或时间字符串
 * @returns {string} 格式化后的时间字符串
 */
App.formatTime = function(date) {
    const d = new Date(date);
    const now = new Date();
    const diff = now - d;

    // 小于1分钟
    if (diff < 60000) {
        return '刚刚';
    }

    // 小于1小时
    if (diff < 3600000) {
        return Math.floor(diff / 60000) + '分钟前';
    }

    // 小于1天
    if (diff < 86400000) {
        return Math.floor(diff / 3600000) + '小时前';
    }

    // 大于1天，显示具体日期
    return d.toLocaleDateString('zh-CN') + ' ' + d.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
    });
};

/**
 * 页面状态管理
 */
App.PageState = {
    get: function(key, defaultValue = null) {
        try {
            const value = localStorage.getItem(`app_${key}`);
            return value ? JSON.parse(value) : defaultValue;
        } catch (e) {
            return defaultValue;
        }
    },

    set: function(key, value) {
        try {
            localStorage.setItem(`app_${key}`, JSON.stringify(value));
        } catch (e) {
            console.warn('无法保存到localStorage:', e);
        }
    },

    remove: function(key) {
        try {
            localStorage.removeItem(`app_${key}`);
        } catch (e) {
            console.warn('无法从localStorage删除:', e);
        }
    }
};

/**
 * 初始化应用
 */
App.init = function() {
    // 设置当前页面
    const path = window.location.pathname;
    App.currentPage = path.replace('/', '') || 'index';

    // 初始化工具提示
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // 初始化其他组件
    App.initComponents();

    console.log('AIDefectDetector应用已初始化');
};

/**
 * 初始化页面组件
 */
App.initComponents = function() {
    // 初始化下拉菜单
    const dropdowns = document.querySelectorAll('.dropdown-toggle');
    dropdowns.forEach(dropdown => {
        if (typeof bootstrap !== 'undefined') {
            new bootstrap.Dropdown(dropdown);
        }
    });

    // 初始化导航高亮
    App.highlightCurrentNav();
};

/**
 * 高亮当前导航项
 */
App.highlightCurrentNav = function() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');

    navLinks.forEach(link => {
        link.classList.remove('active');
        const href = link.getAttribute('href');
        if (href === currentPath ||
            (currentPath !== '/' && href && currentPath.startsWith(href))) {
            link.classList.add('active');
        }
    });
};

/**
 * 页面加载完成后初始化
 */
document.addEventListener('DOMContentLoaded', function() {
    App.init();
});

// 导出到全局
window.App = App;
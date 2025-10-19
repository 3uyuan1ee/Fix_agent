// AIDefectDetector Web应用主要JavaScript文件

// 全局变量
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

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('AIDefectDetector Web应用初始化中...');

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
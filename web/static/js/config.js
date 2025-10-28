/**
 * API配置页面JavaScript逻辑
 * 实现LLM供应商配置、API Key管理、连接测试等功能
 */

// 配置页面状态管理
const ConfigManager = {
    currentProvider: null,
    configData: {},
    originalConfig: {},

    // 初始化配置页面
    init: function() {
        this.bindEvents();
        this.loadCurrentConfig();
        this.setupFormValidation();
    },

    // 绑定事件监听器
    bindEvents: function() {
        // 供应商卡片点击事件
        document.querySelectorAll('.provider-card').forEach(card => {
            card.addEventListener('click', (e) => {
                // 如果点击的是表单元素，不触发卡片选择
                if (e.target.closest('form, button, input, select')) {
                    return;
                }
                this.selectProvider(card.dataset.provider);
            });
        });

        // API Key显示/隐藏切换
        document.querySelectorAll('.api-key-toggle').forEach(btn => {
            btn.addEventListener('click', () => {
                const targetId = btn.dataset.target;
                const input = document.getElementById(targetId);
                const icon = btn.querySelector('i');

                if (input.type === 'password') {
                    input.type = 'text';
                    icon.className = 'fas fa-eye-slash';
                } else {
                    input.type = 'password';
                    icon.className = 'fas fa-eye';
                }
            });
        });

        // 测试连接按钮
        document.querySelectorAll('.test-connection-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.testConnection(btn.dataset.provider);
            });
        });

        // 高级配置切换
        document.querySelectorAll('.advanced-toggle').forEach(btn => {
            btn.addEventListener('click', () => {
                const options = btn.nextElementSibling;
                if (options.style.display === 'none') {
                    options.style.display = 'block';
                    btn.innerHTML = '<i class="fas fa-cog me-1"></i>收起高级配置';
                } else {
                    options.style.display = 'none';
                    btn.innerHTML = '<i class="fas fa-cog me-1"></i>高级配置';
                }
            });
        });

        // 保存配置按钮
        document.getElementById('save-config-btn').addEventListener('click', () => {
            this.saveConfig();
        });

        // 保存到环境变量按钮
        document.getElementById('save-env-btn').addEventListener('click', () => {
            this.saveToEnvironment();
        });

        // 重置配置按钮
        document.getElementById('reset-btn').addEventListener('click', () => {
            this.resetConfig();
        });

        // 确认保存按钮
        document.getElementById('confirm-save-btn').addEventListener('click', () => {
            this.confirmSave();
        });

        // 表单输入变化监听
        document.querySelectorAll('.config-form input, .config-form select').forEach(input => {
            input.addEventListener('input', () => {
                this.markFormChanged();
            });
        });
    },

    // 选择LLM供应商
    selectProvider: function(provider) {
        // 更新UI状态
        document.querySelectorAll('.provider-card').forEach(card => {
            card.classList.remove('selected');
        });
        document.querySelector(`[data-provider="${provider}"]`).classList.add('selected');

        // 显示对应配置表单
        document.querySelectorAll('.config-form').forEach(form => {
            form.classList.remove('show');
        });
        document.getElementById(`${provider}-config`).classList.add('show');

        this.currentProvider = provider;

        // 更新侧边栏导航状态
        App.Sidebar.setActive('config');
    },

    // 加载当前配置
    loadCurrentConfig: function() {
        App.get('/api/config')
            .then(data => {
                this.configData = data.config || {};
                this.originalConfig = JSON.parse(JSON.stringify(this.configData));
                this.populateForms();

                // 如果有已配置的供应商，自动选中
                if (this.configData.llm_providers) {
                    const firstProvider = Object.keys(this.configData.llm_providers)[0];
                    if (firstProvider) {
                        this.selectProvider(firstProvider);
                    }
                }
            })
            .catch(error => {
                App.handleError(error, '加载配置');
                // 显示默认供应商
                this.selectProvider('openai');
            });
    },

    // 填充表单数据
    populateForms: function() {
        if (!this.configData.llm_providers) return;

        Object.keys(this.configData.llm_providers).forEach(provider => {
            const config = this.configData.llm_providers[provider];
            const form = document.getElementById(`${provider}-form`);

            if (form) {
                // 填充API Key（隐藏显示）
                const apiKeyInput = form.querySelector(`#${provider}-api-key`);
                if (apiKeyInput && config.api_key) {
                    // 如果是环境变量格式，显示占位符
                    if (config.api_key.startsWith('${')) {
                        apiKeyInput.placeholder = `已配置: ${config.api_key}`;
                        apiKeyInput.value = '';
                    } else {
                        apiKeyInput.value = config.api_key;
                    }
                }

                // 填充其他字段
                const fields = ['base_url', 'model', 'temperature', 'max_tokens', 'timeout'];
                fields.forEach(field => {
                    const input = form.querySelector(`#${provider}-${field}`);
                    if (input && config[field]) {
                        input.value = config[field];
                    }
                });

                // 填充高级配置
                const advancedFields = ['max_tokens', 'timeout'];
                advancedFields.forEach(field => {
                    const input = form.querySelector(`#${provider}-${field}`);
                    if (input && config[field]) {
                        input.value = config[field];
                    }
                });
            }
        });
    },

    // 设置表单验证
    setupFormValidation: function() {
        // API Key格式验证
        document.querySelectorAll('input[id$="-api-key"]').forEach(input => {
            input.addEventListener('blur', () => {
                this.validateApiKey(input);
            });
        });

        // URL格式验证
        document.querySelectorAll('input[type="url"]').forEach(input => {
            input.addEventListener('blur', () => {
                this.validateUrl(input);
            });
        });

        // 数值范围验证
        document.querySelectorAll('input[type="number"]').forEach(input => {
            input.addEventListener('blur', () => {
                this.validateNumber(input);
            });
        });
    },

    // 验证API Key格式
    validateApiKey: function(input) {
        const value = input.value.trim();
        const provider = input.id.replace('-api-key', '');

        if (!value) {
            this.showFieldError(input, 'API Key不能为空');
            return false;
        }

        // 不同供应商的API Key格式验证
        const patterns = {
            openai: /^sk-[A-Za-z0-9]{48}$/,
            zhipu: /^[A-Za-z0-9]{32}\.[A-Za-z0-9]+$/,
            anthropic: /^sk-ant-[A-Za-z0-9]{95}$/
        };

        if (patterns[provider] && !patterns[provider].test(value)) {
            this.showFieldError(input, `API Key格式不正确，请检查`);
            return false;
        }

        this.clearFieldError(input);
        return true;
    },

    // 验证URL格式
    validateUrl: function(input) {
        const value = input.value.trim();

        if (value && !this.isValidUrl(value)) {
            this.showFieldError(input, '请输入有效的URL格式');
            return false;
        }

        this.clearFieldError(input);
        return true;
    },

    // 验证数值范围
    validateNumber: function(input) {
        const value = parseFloat(input.value);
        const min = parseFloat(input.min);
        const max = parseFloat(input.max);

        if (isNaN(value)) {
            this.showFieldError(input, '请输入有效数字');
            return false;
        }

        if (min !== undefined && value < min) {
            this.showFieldError(input, `数值不能小于${min}`);
            return false;
        }

        if (max !== undefined && value > max) {
            this.showFieldError(input, `数值不能大于${max}`);
            return false;
        }

        this.clearFieldError(input);
        return true;
    },

    // 测试API连接
    testConnection: function(provider) {
        const btn = document.querySelector(`[data-provider="${provider}"].test-connection-btn`);
        const originalText = btn.innerHTML;

        // 获取表单数据
        const formData = this.getFormData(provider);

        if (!formData.api_key) {
            App.showAlert('请先输入API Key', 'warning');
            return;
        }

        // 更新按钮状态
        btn.disabled = true;
        btn.innerHTML = '<span class="loading me-2"></span>测试中...';

        // 添加测试状态指示器
        this.addStatusIndicator(provider, 'testing');

        App.post('/api/config/test', {
            provider: provider,
            config: formData
        })
        .then(data => {
            if (data.success) {
                App.showAlert(`${this.getProviderName(provider)} API连接测试成功！`, 'success');
                this.addStatusIndicator(provider, 'success');
            } else {
                App.showAlert(`连接测试失败: ${data.error}`, 'danger');
                this.addStatusIndicator(provider, 'error');
            }
        })
        .catch(error => {
            App.handleError(error, 'API连接测试');
            this.addStatusIndicator(provider, 'error');
        })
        .finally(() => {
            // 恢复按钮状态
            btn.disabled = false;
            btn.innerHTML = originalText;
        });
    },

    // 获取表单数据
    getFormData: function(provider) {
        const form = document.getElementById(`${provider}-form`);
        const formData = {};

        // 获取基本字段
        const fields = ['api_key', 'base_url', 'model', 'temperature', 'max_tokens', 'timeout'];
        fields.forEach(field => {
            const input = form.querySelector(`#${provider}-${field}`);
            if (input && input.value.trim()) {
                formData[field] = field === 'temperature' || field === 'max_tokens' || field === 'timeout'
                    ? parseFloat(input.value)
                    : input.value.trim();
            }
        });

        return formData;
    },

    // 保存配置
    saveConfig: function() {
        if (!this.validateCurrentForm()) {
            App.showAlert('请修正表单错误后再保存', 'warning');
            return;
        }

        // 显示确认对话框
        const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
        modal.show();
    },

    // 确认保存
    confirmSave: function() {
        const allConfigs = {};

        // 获取所有供应商的配置
        ['openai', 'zhipu', 'anthropic'].forEach(provider => {
            const form = document.getElementById(`${provider}-form`);
            if (form) {
                const formData = this.getFormData(provider);
                if (Object.keys(formData).length > 0) {
                    allConfigs[provider] = formData;
                }
            }
        });

        const saveData = {
            llm_providers: allConfigs,
            web: this.configData.web || {},
            static_analysis: this.configData.static_analysis || {},
            deep_analysis: this.configData.deep_analysis || {}
        };

        App.post('/api/config', saveData)
            .then(data => {
                if (data.success) {
                    App.showAlert('配置保存成功！', 'success');
                    this.configData = data.config;
                    this.originalConfig = JSON.parse(JSON.stringify(this.configData));

                    // 关闭确认对话框
                    const modal = bootstrap.Modal.getInstance(document.getElementById('confirmModal'));
                    modal.hide();
                } else {
                    App.showAlert(`保存失败: ${data.error}`, 'danger');
                }
            })
            .catch(error => {
                App.handleError(error, '保存配置');
            });
    },

    // 保存到环境变量
    saveToEnvironment: function() {
        if (!this.validateCurrentForm()) {
            App.showAlert('请修正表单错误后再保存', 'warning');
            return;
        }

        const formData = this.getFormData(this.currentProvider);
        if (!formData.api_key) {
            App.showAlert('请先输入API Key', 'warning');
            return;
        }

        App.post('/api/config/env', {
            provider: this.currentProvider,
            api_key: formData.api_key
        })
        .then(data => {
            if (data.success) {
                App.showAlert('API Key已保存到环境变量！', 'success');
            } else {
                App.showAlert(`保存失败: ${data.error}`, 'danger');
            }
        })
        .catch(error => {
            App.handleError(error, '保存环境变量');
        });
    },

    // 重置配置
    resetConfig: function() {
        if (confirm('确定要重置所有配置吗？这将清空所有已保存的配置。')) {
            // 清空所有表单
            document.querySelectorAll('.config-form').forEach(form => {
                form.reset();
            });

            // 清空配置数据
            this.configData = {};
            this.originalConfig = {};

            App.showAlert('配置已重置', 'info');
        }
    },

    // 验证当前表单
    validateCurrentForm: function() {
        if (!this.currentProvider) return true;

        const form = document.getElementById(`${this.currentProvider}-form`);
        let isValid = true;

        // 验证必填字段
        const requiredFields = ['api_key', 'model'];
        requiredFields.forEach(field => {
            const input = form.querySelector(`#${this.currentProvider}-${field}`);
            if (input && !input.value.trim()) {
                this.showFieldError(input, '此字段为必填项');
                isValid = false;
            }
        });

        return isValid;
    },

    // 标记表单已修改
    markFormChanged: function() {
        // 可以在这里添加表单修改标记逻辑
    },

    // 显示字段错误
    showFieldError: function(input, message) {
        this.clearFieldError(input);

        input.classList.add('is-invalid');

        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        feedback.textContent = message;

        input.parentNode.appendChild(feedback);
    },

    // 清除字段错误
    clearFieldError: function(input) {
        input.classList.remove('is-invalid');

        const feedback = input.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.remove();
        }
    },

    // 添加状态指示器
    addStatusIndicator: function(provider, status) {
        const card = document.querySelector(`[data-provider="${provider}"]`);
        const existing = card.querySelector('.status-indicator');

        if (existing) {
            existing.remove();
        }

        const indicator = document.createElement('span');
        indicator.className = `status-indicator ${status}`;

        const title = card.querySelector('.provider-title');
        title.appendChild(indicator);
    },

    // 获取供应商名称
    getProviderName: function(provider) {
        const names = {
            openai: 'OpenAI',
            zhipu: '智谱AI',
            anthropic: 'Anthropic Claude'
        };
        return names[provider] || provider;
    },

    // 检查URL是否有效
    isValidUrl: function(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 设置当前页面
    App.Sidebar.setActive('config');

    // 初始化配置管理器
    ConfigManager.init();
});
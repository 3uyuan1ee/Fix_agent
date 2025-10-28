/**
 * 静态分析页面JavaScript逻辑
 * 实现文件上传、工具选择、分析进度管理、结果展示等功能
 */

// 静态分析页面状态管理
const StaticAnalysisManager = {
    // 页面状态
    projectId: null,
    projectPath: null,
    selectedTools: [],
    analysisTaskId: null,
    analysisStatus: null,
    analysisResults: null,

    // 分析配置
    analysisConfig: {
        depth: 'standard',
        includeTests: false,
        maxIssues: 100,
        severity: ['critical', 'warning', 'info'],
        categories: ['security', 'performance', 'style']
    },

    // 初始化页面
    init: function() {
        this.bindEvents();
        this.initializeTools();
        this.setupFormValidation();
        this.restorePreviousSession();
    },

    // 绑定事件监听器
    bindEvents: function() {
        // 文件上传相关事件
        this.bindFileUploadEvents();

        // 路径输入相关事件
        this.bindPathInputEvents();

        // 工具选择相关事件
        this.bindToolSelectionEvents();

        // 分析配置相关事件
        this.bindAnalysisConfigEvents();

        // 分析控制相关事件
        this.bindAnalysisControlEvents();

        // 结果展示相关事件
        this.bindResultsEvents();
    },

    // 绑定文件上传事件
    bindFileUploadEvents: function() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const selectFileBtn = document.getElementById('selectFileBtn');

        // 点击选择文件按钮
        selectFileBtn.addEventListener('click', (e) => {
            e.preventDefault();
            fileInput.click();
        });

        // 文件选择变化
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.uploadFile(file);
            }
        });

        // 拖拽上传
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.uploadFile(files[0]);
            }
        });
    },

    // 绑定路径输入事件
    bindPathInputEvents: function() {
        const projectPath = document.getElementById('projectPath');
        const browseBtn = document.getElementById('browseBtn');
        const validatePathBtn = document.getElementById('validatePathBtn');

        // 浏览按钮（在实际应用中可能需要特殊处理）
        browseBtn.addEventListener('click', () => {
            App.showAlert('请手动输入项目路径或使用文件上传功能', 'info');
        });

        // 路径输入验证
        projectPath.addEventListener('input', () => {
            this.clearPathValidation();
            this.checkFormCompletion();
        });

        // 验证路径按钮
        validatePathBtn.addEventListener('click', () => {
            this.validateProjectPath();
        });
    },

    // 绑定工具选择事件
    bindToolSelectionEvents: function() {
        // 选择模式切换
        document.querySelectorAll('input[name="selectionMode"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.switchSelectionMode(e.target.value);
            });
        });

        // 预设选择
        document.querySelectorAll('.tool-preset-card').forEach(card => {
            card.addEventListener('click', () => {
                this.selectToolPreset(card.dataset.preset);
            });
        });

        // 自定义工具选择
        document.querySelectorAll('.tool-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateSelectedTools();
                this.checkFormCompletion();
            });
        });

        // 工具配置展开/收起
        document.querySelectorAll('.config-toggle-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const configOptions = btn.closest('.tool-config').querySelector('.config-options');
                const isVisible = configOptions.style.display !== 'none';

                if (isVisible) {
                    configOptions.style.display = 'none';
                    btn.innerHTML = '<i class="fas fa-cog me-1"></i>自定义参数';
                } else {
                    configOptions.style.display = 'block';
                    btn.innerHTML = '<i class="fas fa-cog me-1"></i>收起参数';
                }
            });
        });
    },

    // 绑定分析配置事件
    bindAnalysisConfigEvents: function() {
        // 分析配置变化
        document.getElementById('analysisConfigForm').addEventListener('change', () => {
            this.updateAnalysisConfig();
        });

        // 严重程度选择
        document.querySelectorAll('input[name^="severity"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateSeverityFilters();
            });
        });

        // 类别选择
        document.querySelectorAll('input[name^="category"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateCategoryFilters();
            });
        });
    },

    // 绑定分析控制事件
    bindAnalysisControlEvents: function() {
        const startBtn = document.getElementById('startAnalysisBtn');

        // 开始分析按钮
        startBtn.addEventListener('click', () => {
            this.startAnalysis();
        });
    },

    // 绑定结果展示事件
    bindResultsEvents: function() {
        // 导出结果按钮
        document.getElementById('exportResultsBtn').addEventListener('click', () => {
            this.showExportModal();
        });

        // 确认导出按钮
        document.getElementById('confirmExportBtn').addEventListener('click', () => {
            this.exportResults();
        });

        // 进入修复模式按钮
        document.getElementById('goToFixBtn').addEventListener('click', () => {
            this.goToFixMode();
        });
    },

    // 初始化工具选择
    initializeTools: function() {
        // 默认选择基础预设
        this.selectToolPreset('basic');
    },

    // 切换选择模式
    switchSelectionMode: function(mode) {
        const quickSelection = document.getElementById('quickSelection');
        const customSelection = document.getElementById('customSelection');

        if (mode === 'quick') {
            quickSelection.style.display = 'block';
            customSelection.style.display = 'none';
        } else {
            quickSelection.style.display = 'none';
            customSelection.style.display = 'block';
        }
    },

    // 选择工具预设
    selectToolPreset: function(preset) {
        // 更新UI状态
        document.querySelectorAll('.tool-preset-card').forEach(card => {
            card.classList.remove('selected');
        });
        document.querySelector(`[data-preset="${preset}"]`).classList.add('selected');

        // 清除自定义选择
        document.querySelectorAll('.tool-checkbox').forEach(checkbox => {
            checkbox.checked = false;
        });
        document.querySelectorAll('.tool-card').forEach(card => {
            card.classList.remove('selected');
        });

        // 根据预设选择工具
        const presetTools = {
            basic: ['pylint', 'flake8', 'mypy'],
            comprehensive: ['pylint', 'bandit', 'mypy', 'vulture'],
            security: ['bandit', 'safety', 'semgrep']
        };

        const tools = presetTools[preset] || [];
        tools.forEach(tool => {
            const checkbox = document.getElementById(`${tool}-check`);
            if (checkbox) {
                checkbox.checked = true;
                checkbox.closest('.tool-card').classList.add('selected');
            }
        });

        this.updateSelectedTools();
        this.checkFormCompletion();
    },

    // 更新选中的工具
    updateSelectedTools: function() {
        this.selectedTools = [];

        document.querySelectorAll('.tool-checkbox:checked').forEach(checkbox => {
            const tool = checkbox.id.replace('-check', '');
            const config = this.getToolConfig(tool);
            this.selectedTools.push({
                name: tool,
                config: config
            });
        });

        // 更新自定义工具卡片的选中状态
        document.querySelectorAll('.tool-card').forEach(card => {
            const checkbox = card.querySelector('.tool-checkbox');
            if (checkbox && checkbox.checked) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
            }
        });
    },

    // 获取工具配置
    getToolConfig: function(tool) {
        const config = {};

        // 根据不同工具获取配置
        switch (tool) {
            case 'pylint':
                const score = document.getElementById('pylint-score');
                const errors = document.getElementById('pylint-errors');
                const warnings = document.getElementById('pylint-warnings');
                const conventions = document.getElementById('pylint-conventions');

                if (score) config.min_score = parseFloat(score.value);
                if (errors) config.check_errors = errors.checked;
                if (warnings) config.check_warnings = warnings.checked;
                if (conventions) config.check_conventions = conventions.checked;
                break;

            case 'flake8':
                const maxLineLength = document.getElementById('flake8-max-line-length');
                const ignore = document.getElementById('flake8-ignore');

                if (maxLineLength) config.max_line_length = parseInt(maxLineLength.value);
                if (ignore && ignore.value) config.ignore = ignore.value.split(',').map(s => s.trim());
                break;

            case 'bandit':
                const level = document.getElementById('bandit-level');
                const confidence = document.getElementById('bandit-confidence');

                if (level) config.level = level.value;
                if (confidence) config.confidence = confidence.value;
                break;

            case 'mypy':
                const strict = document.getElementById('mypy-strict');
                const implicitOptional = document.getElementById('mypy-implicit-optional');

                if (strict) config.strict = strict.checked;
                if (implicitOptional) config.implicit_optional = implicitOptional.checked;
                break;

            case 'vulture':
                const minConfidence = document.getElementById('vulture-min-confidence');
                const excludeTests = document.getElementById('vulture-exclude-tests');

                if (minConfidence) config.min_confidence = parseInt(minConfidence.value);
                if (excludeTests) config.exclude_tests = excludeTests.checked;
                break;
        }

        return config;
    },

    // 上传文件
    uploadFile: function(file) {
        const uploadProgress = document.getElementById('uploadProgress');
        const uploadContent = document.querySelector('.upload-content');

        // 验证文件
        if (!this.validateFile(file)) {
            return;
        }

        // 显示上传进度
        uploadContent.style.display = 'none';
        uploadProgress.style.display = 'block';

        // 创建FormData
        const formData = new FormData();
        formData.append('file', file);

        // 上传文件
        App.upload('/api/upload', formData, {
            onProgress: (progress) => {
                this.updateUploadProgress(progress);
            }
        })
        .then(data => {
            if (data.success) {
                this.projectId = data.file_id;
                this.projectPath = data.path;
                App.showAlert('文件上传成功！', 'success');
                this.checkFormCompletion();
            } else {
                App.showAlert(`上传失败: ${data.error}`, 'danger');
                this.resetUploadUI();
            }
        })
        .catch(error => {
            App.handleError(error, '文件上传');
            this.resetUploadUI();
        });
    },

    // 验证文件
    validateFile: function(file) {
        // 检查文件类型
        const allowedTypes = ['.zip', '.tar', '.gz'];
        const fileName = file.name.toLowerCase();
        const isAllowed = allowedTypes.some(type => fileName.endsWith(type));

        if (!isAllowed) {
            App.showAlert('不支持的文件类型，请上传 .zip, .tar 或 .gz 文件', 'warning');
            return false;
        }

        // 检查文件大小（50MB）
        const maxSize = 50 * 1024 * 1024;
        if (file.size > maxSize) {
            App.showAlert('文件太大，请上传小于 50MB 的文件', 'warning');
            return false;
        }

        return true;
    },

    // 更新上传进度
    updateUploadProgress: function(progress) {
        const progressBar = document.querySelector('.upload-progress .progress-bar');
        const progressText = document.querySelector('.upload-progress p');

        const percentage = Math.round(progress);
        progressBar.style.width = `${percentage}%`;
        progressText.textContent = `正在上传... ${percentage}%`;
    },

    // 重置上传UI
    resetUploadUI: function() {
        const uploadProgress = document.getElementById('uploadProgress');
        const uploadContent = document.querySelector('.upload-content');

        uploadProgress.style.display = 'none';
        uploadContent.style.display = 'block';

        // 重置进度条
        const progressBar = document.querySelector('.upload-progress .progress-bar');
        progressBar.style.width = '0%';
    },

    // 验证项目路径
    validateProjectPath: function() {
        const path = document.getElementById('projectPath').value.trim();

        if (!path) {
            this.showPathValidation('请输入项目路径', 'warning');
            return;
        }

        App.post('/api/validate-path', { path: path })
            .then(data => {
                if (data.valid) {
                    this.projectPath = path;
                    this.showPathValidation(data.message, 'success');
                    this.checkFormCompletion();
                } else {
                    this.showPathValidation(data.error, 'danger');
                }
            })
            .catch(error => {
                App.handleError(error, '路径验证');
            });
    },

    // 显示路径验证结果
    showPathValidation: function(message, type) {
        const resultDiv = document.getElementById('pathValidationResult');
        const alertClass = type === 'success' ? 'alert-success' :
                          type === 'warning' ? 'alert-warning' : 'alert-danger';

        resultDiv.innerHTML = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
    },

    // 清除路径验证结果
    clearPathValidation: function() {
        const resultDiv = document.getElementById('pathValidationResult');
        resultDiv.innerHTML = '';
    },

    // 更新分析配置
    updateAnalysisConfig: function() {
        const depth = document.getElementById('analysisDepth').value;
        const includeTests = document.getElementById('includeTests').value === 'true';
        const maxIssues = parseInt(document.getElementById('maxIssues').value);

        this.analysisConfig = {
            ...this.analysisConfig,
            depth: depth,
            includeTests: includeTests,
            maxIssues: maxIssues
        };
    },

    // 更新严重程度过滤器
    updateSeverityFilters: function() {
        const severities = [];
        document.querySelectorAll('input[name^="severity"]:checked').forEach(checkbox => {
            severities.push(checkbox.value);
        });
        this.analysisConfig.severity = severities;
    },

    // 更新类别过滤器
    updateCategoryFilters: function() {
        const categories = [];
        document.querySelectorAll('input[name^="category"]:checked').forEach(checkbox => {
            categories.push(checkbox.value);
        });
        this.analysisConfig.categories = categories;
    },

    // 检查表单是否完成
    checkFormCompletion: function() {
        const hasProject = this.projectId || this.projectPath;
        const hasTools = this.selectedTools.length > 0;
        const startBtn = document.getElementById('startAnalysisBtn');

        if (hasProject && hasTools) {
            startBtn.disabled = false;
        } else {
            startBtn.disabled = true;
        }
    },

    // 设置表单验证
    setupFormValidation: function() {
        // 可以在这里添加表单验证逻辑
    },

    // 恢复之前的会话
    restorePreviousSession: function() {
        // 可以在这里添加会话恢复逻辑
    },

    // 开始分析
    startAnalysis: function() {
        if (!this.projectId && !this.projectPath) {
            App.showAlert('请先上传项目文件或输入项目路径', 'warning');
            return;
        }

        if (this.selectedTools.length === 0) {
            App.showAlert('请至少选择一个分析工具', 'warning');
            return;
        }

        // 构建分析请求
        const requestData = {
            project_path: this.projectPath,
            project_id: this.projectId,
            tools: this.selectedTools,
            config: this.analysisConfig,
            mode: 'static'
        };

        // 显示进度卡片
        this.showAnalysisProgress();

        // 启动分析
        App.post('/api/static/start', requestData)
            .then(data => {
                if (data.success) {
                    this.analysisTaskId = data.task_id;
                    App.showAlert('分析任务已启动！', 'success');
                    this.startProgressMonitoring();
                } else {
                    App.showAlert(`启动分析失败: ${data.error}`, 'danger');
                    this.hideAnalysisProgress();
                }
            })
            .catch(error => {
                App.handleError(error, '启动分析');
                this.hideAnalysisProgress();
            });
    },

    // 显示分析进度
    showAnalysisProgress: function() {
        const progressCard = document.getElementById('analysisProgressCard');
        progressCard.style.display = 'block';
        progressCard.classList.add('fade-in');

        // 滚动到进度卡片
        progressCard.scrollIntoView({ behavior: 'smooth' });
    },

    // 隐藏分析进度
    hideAnalysisProgress: function() {
        const progressCard = document.getElementById('analysisProgressCard');
        progressCard.style.display = 'none';
    },

    // 开始进度监控
    startProgressMonitoring: function() {
        if (!this.analysisTaskId) return;

        const monitorInterval = setInterval(() => {
            App.get(`/api/static/status/${this.analysisTaskId}`)
                .then(data => {
                    this.updateProgress(data);

                    if (data.status === 'completed') {
                        clearInterval(monitorInterval);
                        this.loadAnalysisResults();
                    } else if (data.status === 'failed') {
                        clearInterval(monitorInterval);
                        App.showAlert('分析失败: ' + (data.error || '未知错误'), 'danger');
                        this.hideAnalysisProgress();
                    }
                })
                .catch(error => {
                    App.handleError(error, '获取分析状态');
                    clearInterval(monitorInterval);
                    this.hideAnalysisProgress();
                });
        }, 2000); // 每2秒检查一次
    },

    // 更新进度显示
    updateProgress: function(data) {
        const progressBar = document.querySelector('.analysis-progress .progress-bar');
        const currentStatus = document.getElementById('currentStatus');
        const analyzedFiles = document.getElementById('analyzedFiles');
        const foundIssues = document.getElementById('foundIssues');
        const remainingTime = document.getElementById('remainingTime');

        // 更新进度条
        progressBar.style.width = `${data.progress || 0}%`;

        // 更新状态文本
        if (data.status === 'running') {
            currentStatus.textContent = '正在分析...';
        } else if (data.status === 'completed') {
            currentStatus.textContent = '分析完成';
        }

        // 更新其他信息
        if (data.analyzed_files !== undefined) {
            analyzedFiles.textContent = `${data.analyzed_files} / ${data.total_files || 0}`;
        }

        if (data.found_issues !== undefined) {
            foundIssues.textContent = data.found_issues;
        }

        if (data.remaining_time) {
            remainingTime.textContent = data.remaining_time;
        }
    },

    // 加载分析结果
    loadAnalysisResults: function() {
        if (!this.analysisTaskId) return;

        App.get(`/api/static/results/${this.analysisTaskId}`)
            .then(data => {
                if (data.success) {
                    this.analysisResults = data;
                    this.displayResults();
                    this.hideAnalysisProgress();
                } else {
                    App.showAlert('获取分析结果失败', 'danger');
                }
            })
            .catch(error => {
                App.handleError(error, '获取分析结果');
            });
    },

    // 显示分析结果
    displayResults: function() {
        const resultsCard = document.getElementById('analysisResultsCard');
        resultsCard.style.display = 'block';
        resultsCard.classList.add('fade-in');

        // 显示结果概览
        this.displayResultsSummary();

        // 显示详细结果
        this.displayResultsDetails();

        // 滚动到结果卡片
        resultsCard.scrollIntoView({ behavior: 'smooth' });
    },

    // 显示结果概览
    displayResultsSummary: function() {
        const summaryDiv = document.getElementById('resultsSummary');
        const analysisInfo = this.analysisResults.analysis_info;

        summaryDiv.innerHTML = `
            <h5 class="mb-3">分析概览</h5>
            <div class="summary-stats">
                <div class="stat-item critical">
                    <div class="stat-number">${analysisInfo.critical_count || 0}</div>
                    <div class="stat-label">严重问题</div>
                </div>
                <div class="stat-item warning">
                    <div class="stat-number">${analysisInfo.warning_count || 0}</div>
                    <div class="stat-label">警告问题</div>
                </div>
                <div class="stat-item info">
                    <div class="stat-number">${analysisInfo.info_count || 0}</div>
                    <div class="stat-label">信息问题</div>
                </div>
                <div class="stat-item total">
                    <div class="stat-number">${analysisInfo.total_issues || 0}</div>
                    <div class="stat-label">总问题数</div>
                </div>
            </div>
            <div class="row mt-3">
                <div class="col-md-6">
                    <p><strong>项目名称:</strong> ${analysisInfo.project_name || '未知项目'}</p>
                    <p><strong>分析模式:</strong> ${analysisInfo.analysis_mode || 'static'}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>分析时间:</strong> ${analysisInfo.analysis_time || '未知'}</p>
                    <p><strong>分析文件数:</strong> ${analysisInfo.total_files_analyzed || 0}</p>
                </div>
            </div>
        `;
    },

    // 显示详细结果
    displayResultsDetails: function() {
        const detailsDiv = document.getElementById('resultsDetails');
        const issues = this.analysisResults.issues || [];

        if (issues.length === 0) {
            detailsDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    恭喜！未发现代码问题。
                </div>
            `;
            return;
        }

        let html = '<h5 class="mb-3">问题详情</h5>';

        // 按严重程度分组显示
        const groupedIssues = this.groupIssuesBySeverity(issues);

        Object.entries(groupedIssues).forEach(([severity, severityIssues]) => {
            html += `<h6 class="mt-4 mb-3">${this.getSeverityLabel(severity)} (${severityIssues.length})</h6>`;

            severityIssues.forEach(issue => {
                html += this.createIssueCard(issue);
            });
        });

        detailsDiv.innerHTML = html;
    },

    // 按严重程度分组问题
    groupIssuesBySeverity: function(issues) {
        return issues.reduce((groups, issue) => {
            const severity = issue.severity || 'info';
            if (!groups[severity]) {
                groups[severity] = [];
            }
            groups[severity].push(issue);
            return groups;
        }, {});
    },

    // 获取严重程度标签
    getSeverityLabel: function(severity) {
        const labels = {
            critical: '严重问题',
            warning: '警告问题',
            info: '信息提示'
        };
        return labels[severity] || '其他问题';
    },

    // 创建问题卡片HTML
    createIssueCard: function(issue) {
        return `
            <div class="issue-card">
                <div class="issue-header ${issue.severity}">
                    <div class="issue-title">
                        <span>${issue.title}</span>
                        <span class="badge bg-secondary">${issue.rule_id || 'N/A'}</span>
                    </div>
                    <div class="issue-meta">
                        <div class="issue-file">
                            <i class="fas fa-file-code me-1"></i>
                            ${issue.file}
                        </div>
                        <div class="issue-line">
                            行 ${issue.line}
                        </div>
                        <div class="issue-category">
                            ${issue.category || 'general'}
                        </div>
                    </div>
                </div>
                <div class="issue-body">
                    <div class="issue-description">${issue.description}</div>
                    ${issue.code ? `<div class="issue-code"><pre>${this.escapeHtml(issue.code)}</pre></div>` : ''}
                    <div class="issue-suggestion">
                        <strong>修复建议:</strong> ${issue.suggestion || '暂无建议'}
                    </div>
                </div>
            </div>
        `;
    },

    // HTML转义
    escapeHtml: function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    // 显示导出模态框
    showExportModal: function() {
        const modal = new bootstrap.Modal(document.getElementById('exportModal'));

        // 设置默认文件名
        const filename = document.getElementById('exportFilename');
        const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
        filename.value = `static_analysis_${timestamp}`;

        modal.show();
    },

    // 导出结果
    exportResults: function() {
        const format = document.getElementById('exportFormat').value;
        const filename = document.getElementById('exportFilename').value;

        App.get(`/api/static/export/${this.analysisTaskId}?format=${format}`)
            .then(data => {
                if (data.success) {
                    this.downloadFile(data.data, data.filename || `${filename}.${format}`);
                    App.showAlert('导出成功！', 'success');

                    // 关闭模态框
                    const modal = bootstrap.Modal.getInstance(document.getElementById('exportModal'));
                    modal.hide();
                } else {
                    App.showAlert('导出失败', 'danger');
                }
            })
            .catch(error => {
                App.handleError(error, '导出结果');
            });
    },

    // 下载文件
    downloadFile: function(content, filename) {
        const blob = new Blob([content], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    },

    // 进入修复模式
    goToFixMode: function() {
        if (!this.analysisTaskId) {
            App.showAlert('没有可修复的分析结果', 'warning');
            return;
        }

        // 跳转到修复模式页面，传递分析任务ID
        window.location.href = `/fix?task_id=${this.analysisTaskId}`;
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 设置当前页面
    App.Sidebar.setActive('static');

    // 初始化静态分析管理器
    StaticAnalysisManager.init();
});
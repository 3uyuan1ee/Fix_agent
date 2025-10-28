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
        App.uploadFile(file, {
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
        const toolNames = this.selectedTools.map(tool => typeof tool === 'string' ? tool : tool.name);
        const requestData = {
            project_path: this.projectPath,
            project_id: this.projectId,
            tools: toolNames,
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

        // 创建过滤和排序控件
        let html = this.createResultsControls();

        // 创建结果展示区域
        html += '<div class="results-container">';
        html += '<div class="results-tabs" id="resultsTabs"></div>';
        html += '<div class="results-content" id="resultsContent"></div>';
        html += '</div>';

        detailsDiv.innerHTML = html;

        // 初始化结果展示
        this.initializeResultsDisplay(issues);
    },

    // 创建结果控制面板
    createResultsControls: function() {
        return `
            <div class="results-controls mb-4">
                <div class="row align-items-center">
                    <div class="col-md-3">
                        <label class="form-label">视图模式:</label>
                        <select class="form-select" id="viewMode">
                            <option value="by_severity">按严重程度</option>
                            <option value="by_file">按文件分类</option>
                            <option value="by_tool">按工具分类</option>
                            <option value="by_category">按问题类别</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">排序方式:</label>
                        <select class="form-select" id="sortOrder">
                            <option value="severity_desc">严重程度 (高到低)</option>
                            <option value="severity_asc">严重程度 (低到高)</option>
                            <option value="file_asc">文件路径 (A-Z)</option>
                            <option value="file_desc">文件路径 (Z-A)</option>
                            <option value="line_asc">行号 (小到大)</option>
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">过滤条件:</label>
                        <div class="filter-controls">
                            <div class="form-check form-check-inline">
                                <input class="form-check-input" type="checkbox" id="filterCritical" value="error" checked>
                                <label class="form-check-label" for="filterCritical">
                                    <span class="badge bg-danger">严重</span>
                                </label>
                            </div>
                            <div class="form-check form-check-inline">
                                <input class="form-check-input" type="checkbox" id="filterWarning" value="warning" checked>
                                <label class="form-check-label" for="filterWarning">
                                    <span class="badge bg-warning text-dark">警告</span>
                                </label>
                            </div>
                            <div class="form-check form-check-inline">
                                <input class="form-check-input" type="checkbox" id="filterInfo" value="info" checked>
                                <label class="form-check-label" for="filterInfo">
                                    <span class="badge bg-info">信息</span>
                                </label>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">搜索:</label>
                        <div class="input-group">
                            <input type="text" class="form-control" id="searchIssues" placeholder="搜索问题...">
                            <button class="btn btn-outline-secondary" type="button" id="clearSearch">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    // 初始化结果展示
    initializeResultsDisplay: function(issues) {
        this.currentIssues = issues;
        this.filteredIssues = [...issues];

        // 绑定控件事件
        this.bindResultsControlsEvents();

        // 初始显示
        this.updateResultsDisplay();
    },

    // 绑定结果控件事件
    bindResultsControlsEvents: function() {
        // 视图模式变化
        document.getElementById('viewMode').addEventListener('change', () => {
            this.updateResultsDisplay();
        });

        // 排序方式变化
        document.getElementById('sortOrder').addEventListener('change', () => {
            this.updateResultsDisplay();
        });

        // 过滤条件变化
        document.querySelectorAll('.filter-controls input').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.applyFilters();
            });
        });

        // 搜索功能
        const searchInput = document.getElementById('searchIssues');
        searchInput.addEventListener('input', () => {
            this.applySearch(searchInput.value);
        });

        // 清除搜索
        document.getElementById('clearSearch').addEventListener('click', () => {
            searchInput.value = '';
            this.applySearch('');
        });
    },

    // 应用过滤器
    applyFilters: function() {
        const enabledSeverities = [];
        document.querySelectorAll('.filter-controls input:checked').forEach(checkbox => {
            enabledSeverities.push(checkbox.value);
        });

        this.filteredIssues = this.currentIssues.filter(issue =>
            enabledSeverities.includes(issue.severity || 'info')
        );

        // 重新应用搜索
        const searchValue = document.getElementById('searchIssues').value;
        if (searchValue) {
            this.applySearch(searchValue);
        } else {
            this.updateResultsDisplay();
        }
    },

    // 应用搜索
    applySearch: function(searchTerm) {
        if (!searchTerm.trim()) {
            this.updateResultsDisplay();
            return;
        }

        const term = searchTerm.toLowerCase();
        this.filteredIssues = this.filteredIssues.filter(issue => {
            return (issue.message && issue.message.toLowerCase().includes(term)) ||
                   (issue.file_path && issue.file_path.toLowerCase().includes(term)) ||
                   (issue.tool_name && issue.tool_name.toLowerCase().includes(term)) ||
                   (issue.issue_type && issue.issue_type.toLowerCase().includes(term));
        });

        this.updateResultsDisplay();
    },

    // 更新结果显示
    updateResultsDisplay: function() {
        const viewMode = document.getElementById('viewMode').value;
        const sortOrder = document.getElementById('sortOrder').value;

        // 排序
        this.sortIssues(this.filteredIssues, sortOrder);

        // 根据视图模式显示
        switch (viewMode) {
            case 'by_file':
                this.displayByFile();
                break;
            case 'by_tool':
                this.displayByTool();
                break;
            case 'by_category':
                this.displayByCategory();
                break;
            case 'by_severity':
            default:
                this.displayBySeverity();
                break;
        }
    },

    // 排序问题
    sortIssues: function(issues, sortOrder) {
        issues.sort((a, b) => {
            switch (sortOrder) {
                case 'severity_desc':
                    return this.getSeverityOrder(b.severity) - this.getSeverityOrder(a.severity);
                case 'severity_asc':
                    return this.getSeverityOrder(a.severity) - this.getSeverityOrder(b.severity);
                case 'file_asc':
                    return (a.file_path || '').localeCompare(b.file_path || '');
                case 'file_desc':
                    return (b.file_path || '').localeCompare(a.file_path || '');
                case 'line_asc':
                    return (a.line || 0) - (b.line || 0);
                default:
                    return 0;
            }
        });
    },

    // 获取严重程度排序权重
    getSeverityOrder: function(severity) {
        const weights = {
            'error': 3,
            'warning': 2,
            'info': 1,
            'low': 0
        };
        return weights[severity] || 0;
    },

    // 按严重程度显示
    displayBySeverity: function() {
        const grouped = this.groupIssuesBy(this.filteredIssues, 'severity');
        this.renderGroupedResults(grouped, 'severity', this.getSeverityLabel);
    },

    // 按文件显示
    displayByFile: function() {
        const grouped = this.groupIssuesBy(this.filteredIssues, 'file_path');
        this.renderGroupedResults(grouped, 'file', (filePath) => {
            const fileName = filePath.split('/').pop() || filePath;
            return `<i class="fas fa-file-code me-1"></i>${fileName}`;
        });
    },

    // 按工具显示
    displayByTool: function() {
        const grouped = this.groupIssuesBy(this.filteredIssues, 'tool_name');
        this.renderGroupedResults(grouped, 'tool', (toolName) => {
            const toolLabels = {
                'ast': 'AST分析',
                'pylint': 'Pylint',
                'flake8': 'Flake8',
                'bandit': 'Bandit'
            };
            return `<i class="fas fa-tools me-1"></i>${toolLabels[toolName] || toolName}`;
        });
    },

    // 按类别显示
    displayByCategory: function() {
        const grouped = this.groupIssuesBy(this.filteredIssues, 'issue_type');
        this.renderGroupedResults(grouped, 'category', (category) => {
            const categoryLabels = {
                'syntax_error': '语法错误',
                'complexity': '复杂度',
                'style': '代码风格',
                'security': '安全问题',
                'performance': '性能问题'
            };
            return `<i class="fas fa-tag me-1"></i>${categoryLabels[category] || category}`;
        });
    },

    // 分组问题
    groupIssuesBy: function(issues, groupBy) {
        return issues.reduce((groups, issue) => {
            const key = issue[groupBy] || 'unknown';
            if (!groups[key]) {
                groups[key] = [];
            }
            groups[key].push(issue);
            return groups;
        }, {});
    },

    // 渲染分组结果
    renderGroupedResults: function(grouped, groupType, labelFormatter) {
        const tabsDiv = document.getElementById('resultsTabs');
        const contentDiv = document.getElementById('resultsContent');

        // 创建标签页
        let tabsHtml = '<ul class="nav nav-tabs" id="resultsTabNav" role="tablist">';
        let contentHtml = '<div class="tab-content" id="resultsTabContent">';

        let isFirst = true;
        Object.entries(grouped).forEach(([key, issues]) => {
            const tabId = `${groupType}_${key.replace(/[^a-zA-Z0-9]/g, '_')}`;
            const isActive = isFirst ? 'active' : '';
            const label = labelFormatter(key);
            const count = issues.length;

            // 创建标签
            tabsHtml += `
                <li class="nav-item" role="presentation">
                    <button class="nav-link ${isActive}" id="${tabId}-tab" data-bs-toggle="tab"
                            data-bs-target="#${tabId}" type="button" role="tab">
                        ${label} <span class="badge bg-secondary ms-1">${count}</span>
                    </button>
                </li>
            `;

            // 创建内容
            contentHtml += `
                <div class="tab-pane fade ${isActive}" id="${tabId}" role="tabpanel">
                    ${this.renderIssuesList(issues)}
                </div>
            `;

            isFirst = false;
        });

        tabsHtml += '</ul>';
        contentHtml += '</div>';

        tabsDiv.innerHTML = tabsHtml;
        contentDiv.innerHTML = contentHtml;
    },

    // 渲染问题列表
    renderIssuesList: function(issues) {
        if (issues.length === 0) {
            return '<p class="text-muted">暂无问题</p>';
        }

        let html = '<div class="issues-list">';

        issues.forEach((issue, index) => {
            html += this.createEnhancedIssueCard(issue, index);
        });

        html += '</div>';
        return html;
    },

    // 创建增强的问题卡片
    createEnhancedIssueCard: function(issue, index) {
        const issueId = `issue_${index}`;
        const severityClass = this.getSeverityClass(issue.severity);
        const severityLabel = this.getSeverityLabel(issue.severity);

        return `
            <div class="issue-card ${severityClass} mb-3" id="${issueId}">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center"
                         data-bs-toggle="collapse" data-bs-target="#${issueId}_body"
                         style="cursor: pointer;">
                        <div class="d-flex align-items-center">
                            <span class="severity-indicator ${severityClass} me-2"></span>
                            <div>
                                <h6 class="mb-1">${this.escapeHtml(issue.message || '未知问题')}</h6>
                                <small class="text-muted">
                                    <i class="fas fa-file-code me-1"></i>${this.escapeHtml(issue.file_path || '未知文件')}
                                    <i class="fas fa-map-marker-alt ms-2 me-1"></i>行 ${issue.line || 0}
                                    <i class="fas fa-tools ms-2 me-1"></i>${issue.tool_name || 'unknown'}
                                </small>
                            </div>
                        </div>
                        <div class="d-flex align-items-center">
                            <span class="badge ${severityClass} me-2">${severityLabel}</span>
                            <i class="fas fa-chevron-down"></i>
                        </div>
                    </div>
                    <div class="collapse" id="${issueId}_body">
                        <div class="card-body">
                            ${this.renderIssueDetails(issue)}
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    // 渲染问题详情
    renderIssueDetails: function(issue) {
        let html = '<div class="issue-details">';

        // 基本信息
        html += `
            <div class="row mb-3">
                <div class="col-md-6">
                    <strong>问题类型:</strong> ${this.escapeHtml(issue.issue_type || '未知')}<br>
                    <strong>规则代码:</strong> ${this.escapeHtml(issue.code || 'N/A')}<br>
                    <strong>置信度:</strong> ${this.escapeHtml(issue.confidence || 'N/A')}
                </div>
                <div class="col-md-6">
                    <strong>列号:</strong> ${issue.column || 0}<br>
                    <strong>严重程度:</strong> <span class="badge ${this.getSeverityClass(issue.severity)}">${this.getSeverityLabel(issue.severity)}</span><br>
                    <strong>检测工具:</strong> ${this.escapeHtml(issue.tool_name || '未知')}
                </div>
            </div>
        `;

        // 问题描述
        if (issue.message) {
            html += `
                <div class="mb-3">
                    <strong>问题描述:</strong>
                    <p class="mb-0">${this.escapeHtml(issue.message)}</p>
                </div>
            `;
        }

        // 源代码片段
        if (issue.source_code) {
            html += `
                <div class="mb-3">
                    <strong>相关代码:</strong>
                    <div class="code-snippet">
                        <pre><code class="language-python">${this.escapeHtml(issue.source_code)}</code></pre>
                    </div>
                </div>
            `;
        }

        // 修复建议
        html += `
            <div class="mb-3">
                <strong>修复建议:</strong>
                <div class="fix-suggestion alert alert-info">
                    <i class="fas fa-lightbulb me-2"></i>
                    ${this.generateFixSuggestion(issue)}
                </div>
            </div>
        `;

        // 操作按钮
        html += `
            <div class="d-flex gap-2">
                <button class="btn btn-sm btn-outline-primary" onclick="StaticAnalysisManager.showIssueDetails('${issue.file_path}', ${issue.line})">
                    <i class="fas fa-eye me-1"></i>查看详情
                </button>
                <button class="btn btn-sm btn-outline-success" onclick="StaticAnalysisManager.goToFix('${issue.file_path}', ${issue.line})">
                    <i class="fas fa-tools me-1"></i>立即修复
                </button>
                <button class="btn btn-sm btn-outline-warning" onclick="StaticAnalysisManager.ignoreIssue('${issue.tool_name}', '${issue.code}')">
                    <i class="fas fa-times me-1"></i>忽略此问题
                </button>
            </div>
        `;

        html += '</div>';
        return html;
    },

    // 获取严重程度样式类
    getSeverityClass: function(severity) {
        const classes = {
            'error': 'bg-danger',
            'warning': 'bg-warning text-dark',
            'info': 'bg-info',
            'low': 'bg-secondary'
        };
        return classes[severity] || 'bg-secondary';
    },

    // 生成修复建议
    generateFixSuggestion: function(issue) {
        const suggestions = {
            'syntax_error': '检查语法是否正确，确保括号、引号等配对',
            'complexity': '考虑将复杂函数拆分为更小的函数',
            'style': '按照代码风格指南调整格式',
            'security': '修复安全漏洞，使用更安全的替代方案',
            'performance': '优化代码以提高性能'
        };

        const baseSuggestion = suggestions[issue.issue_type] || '请检查代码并进行相应修复';
        const toolSpecific = this.getToolSpecificSuggestion(issue);

        return toolSpecific || baseSuggestion;
    },

    // 获取工具特定建议
    getToolSpecificSuggestion: function(issue) {
        if (!issue.code) return null;

        const toolSuggestions = {
            'pylint': {
                'C0111': '添加文档字符串说明函数用途',
                'W0612': '删除未使用的变量',
                'R0913': '减少函数参数数量'
            },
            'flake8': {
                'E501': '缩短行长度或调整代码格式',
                'W293': '在文件末尾添加空行',
                'F401': '删除未使用的导入'
            },
            'bandit': {
                'B101': '移除或保护 assert 语句',
                'B301': '使用更安全的序列化方法',
                'B501': '验证请求数据，防止 SSRF 攻击'
            }
        };

        const tool = issue.tool_name;
        const code = issue.code;

        if (toolSuggestions[tool] && toolSuggestions[tool][code]) {
            return toolSuggestions[tool][code];
        }

        return null;
    },

    // 显示问题详情
    showIssueDetails: function(filePath, line) {
        // 这里可以实现显示更多详情的逻辑
        App.showAlert(`查看文件详情: ${filePath}:${line}`, 'info');
    },

    // 跳转到修复
    goToFix: function(filePath, line) {
        if (!this.analysisTaskId) {
            App.showAlert('没有可修复的分析结果', 'warning');
            return;
        }

        // 跳转到修复页面，传递位置信息
        window.location.href = `/fix?task_id=${this.analysisTaskId}&file=${encodeURIComponent(filePath)}&line=${line}`;
    },

    // 忽略问题
    ignoreIssue: function(toolName, code) {
        App.showAlert(`已忽略 ${toolName} 的问题 ${code}`, 'success');
        // 这里可以实现忽略问题的逻辑
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
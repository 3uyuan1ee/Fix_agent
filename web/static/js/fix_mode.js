/**
 * 修复模式JavaScript逻辑
 * 实现修复建议管理、代码对比、批量操作等功能
 */

// 修复模式管理器
const FixModeManager = {
    // 状态管理
    state: {
        currentTaskId: null,
        currentIssueId: null,
        fixSuggestions: [],
        selectedSuggestions: [],
        appliedSuggestions: [],
        rejectedSuggestions: [],
        isProcessing: false,
        currentProgress: 0,
        batchMode: false,
        editMode: false,
        currentEditingSuggestion: null
    },

    // 配置选项
    config: {
        maxConcurrentFixes: 5,
        autoBackup: true,
        enableRealTimeValidation: true,
        enableCodeFormatting: true
    },

    // DOM元素引用
    elements: {},

    // 初始化
    init: function() {
        this.cacheElements();
        this.bindEvents();
        this.loadFromURL();
        this.initializeDiffViewer();
    },

    // 缓存DOM元素
    cacheElements: function() {
        this.elements = {
            // 主要容器
            fixContainer: document.querySelector('.fix-container'),
            suggestionsContainer: document.getElementById('suggestionsContainer'),

            // 工具栏
            toolbar: document.querySelector('.fix-toolbar'),
            batchModeToggle: document.getElementById('batchModeToggle'),
            selectAllBtn: document.getElementById('selectAllBtn'),

            // 操作按钮
            applyAllBtn: document.getElementById('applyAllBtn'),
            applySelectedBtn: document.getElementById('applySelectedBtn'),
            cancelBtn: document.getElementById('cancelBtn'),

            // 进度显示
            progressContainer: document.getElementById('progressContainer'),
            progressBar: document.getElementById('progressBar'),
            progressText: document.getElementById('progressText'),

            // 结果显示
            resultsContainer: document.getElementById('resultsContainer'),

            // 模态框
            editModal: document.getElementById('editModal'),
            confirmModal: document.getElementById('confirmModal'),

            // 统计信息
            totalIssues: document.getElementById('totalIssues'),
            fixedIssues: document.getElementById('fixedIssues'),
            remainingIssues: document.getElementById('remainingIssues'),
            successRate: document.getElementById('successRate')
        };
    },

    // 绑定事件监听器
    bindEvents: function() {
        // 工具栏事件
        if (this.elements.batchModeToggle) {
            this.elements.batchModeToggle.addEventListener('change', () => this.toggleBatchMode());
        }

        if (this.elements.selectAllBtn) {
            this.elements.selectAllBtn.addEventListener('click', () => this.selectAllSuggestions());
        }

        // 操作按钮事件
        if (this.elements.applyAllBtn) {
            this.elements.applyAllBtn.addEventListener('click', () => this.applyAllFixes());
        }

        if (this.elements.applySelectedBtn) {
            this.elements.applySelectedBtn.addEventListener('click', () => this.applySelectedFixes());
        }

        if (this.elements.cancelBtn) {
            this.elements.cancelBtn.addEventListener('click', () => this.cancelOperation());
        }

        // 事件委托处理动态元素
        if (this.elements.suggestionsContainer) {
            this.elements.suggestionsContainer.addEventListener('click', (e) => this.handleSuggestionClick(e));
        }

        // 模态框事件
        this.bindModalEvents();

        // 键盘快捷键
        this.bindKeyboardEvents();

        // 拖拽事件
        this.bindDragEvents();
    },

    // 绑定模态框事件
    bindModalEvents: function() {
        // 编辑模态框
        const editModal = document.getElementById('editModal');
        if (editModal) {
            const cancelEditBtn = editModal.querySelector('.cancel-edit-btn');
            const saveEditBtn = editModal.querySelector('.save-edit-btn');
            const closeBtn = editModal.querySelector('.close-modal-btn');

            if (cancelEditBtn) {
                cancelEditBtn.addEventListener('click', () => this.closeEditModal());
            }

            if (saveEditBtn) {
                saveEditBtn.addEventListener('click', () => this.saveEditChanges());
            }

            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.closeEditModal());
            }
        }

        // 确认模态框
        const confirmModal = document.getElementById('confirmModal');
        if (confirmModal) {
            const confirmBtn = confirmModal.querySelector('.confirm-btn');
            const cancelBtn = confirmModal.querySelector('.cancel-btn');

            if (confirmBtn) {
                confirmBtn.addEventListener('click', () => this.confirmOperation());
            }

            if (cancelBtn) {
                cancelBtn.addEventListener('click', () => this.closeConfirmModal());
            }
        }
    },

    // 绑定键盘快捷键
    bindKeyboardEvents: function() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + A: 全选
            if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
                if (!e.target.matches('input, textarea')) {
                    e.preventDefault();
                    this.selectAllSuggestions();
                }
            }

            // Ctrl/Cmd + Enter: 应用所有修复
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.applyAllFixes();
            }

            // Escape: 取消操作
            if (e.key === 'Escape') {
                if (this.state.isProcessing) {
                    this.cancelOperation();
                } else if (this.state.editMode) {
                    this.closeEditModal();
                }
            }
        });
    },

    // 绑定拖拽事件
    bindDragEvents: function() {
        // 实现文件拖拽到修复区域
        const dropZone = document.querySelector('.fix-drop-zone');
        if (dropZone) {
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('dragover');
            });

            dropZone.addEventListener('dragleave', () => {
                dropZone.classList.remove('dragover');
            });

            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('dragover');
                this.handleDrop(e);
            });
        }
    },

    // 从URL加载参数
    loadFromURL: function() {
        const urlParams = new URLSearchParams(window.location.search);
        this.state.currentTaskId = urlParams.get('task_id');
        this.state.currentIssueId = urlParams.get('issue_id');

        if (this.state.currentTaskId) {
            this.loadFixSuggestions();
        } else {
            this.showError('缺少必要的参数：task_id');
        }
    },

    // 初始化代码差异查看器
    initializeDiffViewer: function() {
        // 检查是否已有diff-viewer.js
        if (typeof createSimpleDiffViewer !== 'undefined') {
            this.diffViewer = createSimpleDiffViewer;
        } else {
            // 创建简单的差异查看器
            this.diffViewer = this.createSimpleDiffViewer();
        }
    },

    // 创建简单的差异查看器
    createSimpleDiffViewer: function() {
        return {
            setCodes: function(original, fixed) {
                this.originalCode = original;
                this.fixedCode = fixed;
            },

            render: function(container) {
                if (!container) return;

                const lines1 = this.originalCode.split('\n');
                const lines2 = this.fixedCode.split('\n');
                const maxLines = Math.max(lines1.length, lines2.length);

                let html = '<div class="diff-viewer">';

                for (let i = 0; i < maxLines; i++) {
                    const line1 = lines1[i] || '';
                    const line2 = lines2[i] || '';
                    const isAdded = !lines1[i] && lines2[i];
                    const isRemoved = lines1[i] && !lines2[i];
                    const isChanged = lines1[i] !== lines2[i];

                    html += '<div class="diff-line ' +
                             (isAdded ? 'added' : isRemoved ? 'removed' : isChanged ? 'changed' : 'unchanged') + '">';
                    html += '<div class="diff-line-number">' + (i + 1) + '</div>';
                    html += '<div class="diff-line-content">' + this.escapeHtml(line2 || line1) + '</div>';
                    html += '</div>';
                }

                html += '</div>';
                container.innerHTML = html;
            },

            getStatistics: function() {
                const lines1 = this.originalCode.split('\n');
                const lines2 = this.fixedCode.split('\n');

                let added = 0;
                let removed = 0;
                let unchanged = 0;

                const maxLines = Math.max(lines1.length, lines2.length);

                for (let i = 0; i < maxLines; i++) {
                    const line1 = lines1[i] || '';
                    const line2 = lines2[i] || '';

                    if (!line1 && line2) {
                        added++;
                    } else if (line1 && !line2) {
                        removed++;
                    } else if (line1 === line2) {
                        unchanged++;
                    }
                }

                return { added, removed, unchanged };
            },

            escapeHtml: function(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
        };
    },

    // 加载修复建议
    loadFixSuggestions: async function() {
        try {
            this.showLoading('正在加载修复建议...');

            const response = await fetch(`/api/fix/suggestions?task_id=${this.state.currentTaskId}`);
            const data = await response.json();

            if (data.success) {
                this.state.fixSuggestions = data.suggestions || [];
                this.renderSuggestions();
                this.updateStatistics();
                this.hideLoading();
            } else {
                this.showError('加载修复建议失败: ' + data.error);
            }
        } catch (error) {
            console.error('Error loading fix suggestions:', error);
            this.showError('加载修复建议时发生错误');
        }
    },

    // 渲染修复建议
    renderSuggestions: function() {
        if (!this.elements.suggestionsContainer) return;

        this.elements.suggestionsContainer.innerHTML = '';

        if (this.state.fixSuggestions.length === 0) {
            this.elements.suggestionsContainer.innerHTML = `
                <div class="text-center p-4">
                    <i class="fas fa-check-circle text-success fa-3x mb-3"></i>
                    <h5>没有发现需要修复的问题</h5>
                    <p class="text-muted">代码质量良好，无需修复</p>
                </div>
            `;
            return;
        }

        this.state.fixSuggestions.forEach((suggestion, index) => {
            const suggestionElement = this.createSuggestionElement(suggestion, index);
            this.elements.suggestionsContainer.appendChild(suggestionElement);
        });
    },

    // 创建修复建议元素
    createSuggestionElement: function(suggestion, index) {
        const template = document.getElementById('fixSuggestionTemplate');
        if (!template) return null;

        const clone = template.content.cloneNode(true);
        const element = clone.querySelector('.fix-suggestion-card');

        // 设置数据属性
        element.dataset.suggestionId = suggestion.id;
        element.dataset.index = index;

        // 填充内容
        this.fillSuggestionContent(element, suggestion);

        // 添加事件监听器
        this.bindSuggestionEvents(element, suggestion);

        return element;
    },

    // 填充修复建议内容
    fillSuggestionContent: function(element, suggestion) {
        // 基本信息
        const titleText = element.querySelector('.title-text');
        if (titleText) {
            titleText.textContent = suggestion.title || '修复建议';
        }

        const severityText = element.querySelector('.severity-text');
        const severityBadge = element.querySelector('.severity-badge');
        if (severityText && severityBadge) {
            severityText.textContent = this.getSeverityText(suggestion.severity);
            severityBadge.className = `severity-badge ${suggestion.severity}`;
        }

        // 问题描述
        const descriptionText = element.querySelector('.description-text');
        if (descriptionText) {
            descriptionText.textContent = suggestion.description || '';
        }

        // 文件信息
        const filePath = element.querySelector('.file-path');
        if (filePath) {
            filePath.textContent = suggestion.file_path || '';
        }

        const lineNumber = element.querySelector('.line-number');
        if (lineNumber) {
            lineNumber.textContent = suggestion.line_number || '';
        }

        // 代码内容
        const originalCode = element.querySelector('.original-code');
        if (originalCode) {
            originalCode.textContent = suggestion.original_code || '';
        }

        const fixedCode = element.querySelector('.fixed-code');
        if (fixedCode) {
            fixedCode.textContent = suggestion.fixed_code || '';
        }

        // 修复说明
        const explanationText = element.querySelector('.explanation-text');
        if (explanationText) {
            explanationText.textContent = suggestion.explanation || '';
        }

        // 设置风险评估
        this.setRiskAssessment(element, suggestion);
    },

    // 设置风险评估
    setRiskAssessment: function(element, suggestion) {
        const riskLevel = suggestion.risk_level || 'medium';
        const riskPointer = element.querySelector('.risk-pointer');

        if (riskPointer) {
            const percentage = this.getRiskPercentage(riskLevel);
            riskPointer.style.left = `${percentage}%`;
        }

        // 设置风险因素
        const breakingChange = element.querySelector('.breaking-change');
        if (breakingChange) {
            breakingChange.textContent = suggestion.breaking_change ? '是' : '否';
        }

        const testCoverage = element.querySelector('.test-coverage');
        if (testCoverage) {
            testCoverage.textContent = suggestion.test_coverage || '未知';
        }

        const rollbackDifficulty = element.querySelector('.rollback-difficulty');
        if (rollbackDifficulty) {
            rollbackDifficulty.textContent = suggestion.rollback_difficulty || '简单';
        }
    },

    // 绑定修复建议事件
    bindSuggestionEvents: function(element, suggestion) {
        // 展开/收起按钮
        const expandBtn = element.querySelector('.expand-btn');
        if (expandBtn) {
            expandBtn.addEventListener('click', () => this.toggleSuggestionExpansion(element));
        }

        // 编辑按钮
        const editBtn = element.querySelector('.edit-btn');
        if (editBtn) {
            editBtn.addEventListener('click', () => this.editSuggestion(suggestion));
        }

        // 忽略按钮
        const dismissBtn = element.querySelector('.dismiss-btn');
        if (dismissBtn) {
            dismissBtn.addEventListener('click', () => this.dismissSuggestion(suggestion));
        }

        // 操作按钮
        const acceptBtn = element.querySelector('.accept-btn');
        if (acceptBtn) {
            acceptBtn.addEventListener('click', () => this.acceptSuggestion(suggestion));
        }

        const modifyBtn = element.querySelector('.modify-btn');
        if (modifyBtn) {
            modifyBtn.addEventListener('click', () => this.modifySuggestion(suggestion));
        }

        const rejectBtn = element.querySelector('.reject-btn');
        if (rejectBtn) {
            rejectBtn.addEventListener('click', () => this.rejectSuggestion(suggestion));
        }

        // 代码操作按钮
        this.bindCodeActionEvents(element, suggestion);
    },

    // 绑定代码操作事件
    bindCodeActionEvents: function(element, suggestion) {
        // 复制原始代码
        const copyOriginalBtn = element.querySelector('.copy-original-btn');
        if (copyOriginalBtn) {
            copyOriginalBtn.addEventListener('click', () => {
                this.copyToClipboard(suggestion.original_code || '');
            });
        }

        // 复制修复后代码
        const copyFixedBtn = element.querySelector('.copy-fixed-btn');
        if (copyFixedBtn) {
            copyFixedBtn.addEventListener('click', () => {
                this.copyToClipboard(suggestion.fixed_code || '');
            });
        }

        // 高亮问题行
        const highlightBtn = element.querySelector('.highlight-original-btn');
        if (highlightBtn) {
            highlightBtn.addEventListener('click', () => {
                this.highlightProblemLine(element, suggestion);
            });
        }

        // 预览修复效果
        const previewBtn = element.querySelector('.preview-fixed-btn');
        if (previewBtn) {
            previewBtn.addEventListener('click', () => {
                this.previewFix(suggestion);
            });
        }
    },

    // 切换建议展开/收起
    toggleSuggestionExpansion: function(element) {
        const content = element.querySelector('.suggestion-content');
        const expandBtn = element.querySelector('.expand-btn i');

        if (content.style.display === 'none') {
            content.style.display = 'block';
            expandBtn.className = 'fas fa-chevron-down';
        } else {
            content.style.display = 'none';
            expandBtn.className = 'fas fa-chevron-right';
        }
    },

    // 编辑修复建议
    editSuggestion: function(suggestion) {
        this.state.currentEditingSuggestion = suggestion;
        this.state.editMode = true;

        // 填充编辑表单
        this.fillEditForm(suggestion);

        // 显示编辑模态框
        this.showEditModal();
    },

    // 填充编辑表单
    fillEditForm: function(suggestion) {
        const modal = document.getElementById('editModal');
        if (!modal) return;

        const explanationEdit = modal.querySelector('.explanation-edit');
        const fixedCodeEdit = modal.querySelector('.fixed-code-edit');
        const riskSlider = modal.querySelector('.risk-slider');
        const riskValue = modal.querySelector('.risk-value');

        if (explanationEdit) {
            explanationEdit.value = suggestion.explanation || '';
        }

        if (fixedCodeEdit) {
            fixedCodeEdit.value = suggestion.fixed_code || '';
        }

        if (riskSlider && riskValue) {
            const riskLevel = suggestion.risk_level || 'medium';
            const riskValueNumeric = this.getRiskNumericValue(riskLevel);
            riskSlider.value = riskValueNumeric;
            riskValue.textContent = riskValueNumeric;

            riskSlider.addEventListener('input', () => {
                riskValue.textContent = riskSlider.value;
            });
        }
    },

    // 显示编辑模态框
    showEditModal: function() {
        const modal = document.getElementById('editModal');
        if (modal) {
            modal.style.display = 'block';
        }
    },

    // 关闭编辑模态框
    closeEditModal: function() {
        const modal = document.getElementById('editModal');
        if (modal) {
            modal.style.display = 'none';
        }
        this.state.editMode = false;
        this.state.currentEditingSuggestion = null;
    },

    // 保存编辑修改
    saveEditChanges: function() {
        if (!this.state.currentEditingSuggestion) return;

        const modal = document.getElementById('editModal');
        if (!modal) return;

        const explanationEdit = modal.querySelector('.explanation-edit');
        const fixedCodeEdit = modal.querySelector('.fixed-code-edit');
        const riskSlider = modal.querySelector('.risk-slider');

        // 更新建议数据
        if (explanationEdit) {
            this.state.currentEditingSuggestion.explanation = explanationEdit.value;
        }

        if (fixedCodeEdit) {
            this.state.currentEditingSuggestion.fixed_code = fixedCodeEdit.value;
        }

        if (riskSlider) {
            this.state.currentEditingSuggestion.risk_level = this.getRiskLevel(riskSlider.value);
        }

        // 重新渲染建议
        this.refreshSuggestion(this.state.currentEditingSuggestion);

        // 关闭模态框
        this.closeEditModal();

        // 显示成功消息
        this.showSuccess('修复建议已更新');
    },

    // 刷新单个建议
    refreshSuggestion: function(suggestion) {
        const element = document.querySelector(`[data-suggestion-id="${suggestion.id}"]`);
        if (element) {
            this.fillSuggestionContent(element, suggestion);
            element.classList.add('updated');
            setTimeout(() => {
                element.classList.remove('updated');
            }, 1000);
        }
    },

    // 忽略修复建议
    dismissSuggestion: function(suggestion) {
        if (confirm('确定要忽略这个修复建议吗？')) {
            this.state.rejectedSuggestions.push(suggestion);
            this.state.fixSuggestions = this.state.fixSuggestions.filter(s => s.id !== suggestion.id);

            // 移除元素
            const element = document.querySelector(`[data-suggestion-id="${suggestion.id}"]`);
            if (element) {
                element.style.opacity = '0';
                element.style.transform = 'translateX(-100%)';
                setTimeout(() => element.remove(), 300);
            }

            this.updateStatistics();
        }
    },

    // 接受修复建议
    acceptSuggestion: async function(suggestion) {
        try {
            this.setSuggestionStatus(suggestion.id, 'processing');

            const response = await fetch('/api/fix/apply', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    suggestion_id: suggestion.id,
                    auto_apply: true
                })
            });

            const data = await response.json();

            if (data.success) {
                this.state.appliedSuggestions.push(suggestion);
                this.setSuggestionStatus(suggestion.id, 'completed');
                this.showSuccess('修复已成功应用');

                // 显示代码差异
                if (data.diff) {
                    this.showDiffResult(suggestion, data.diff);
                }
            } else {
                this.setSuggestionStatus(suggestion.id, 'failed');
                this.showError('修复应用失败: ' + data.error);
            }
        } catch (error) {
            console.error('Error applying fix:', error);
            this.setSuggestionStatus(suggestion.id, 'failed');
            this.showError('应用修复时发生错误');
        }

        this.updateStatistics();
    },

    // 修改修复建议
    modifySuggestion: function(suggestion) {
        this.editSuggestion(suggestion);
    },

    // 拒绝修复建议
    rejectSuggestion: function(suggestion) {
        if (confirm('确定要拒绝这个修复建议吗？')) {
            this.state.rejectedSuggestions.push(suggestion);

            // 移除或标记为已拒绝
            const element = document.querySelector(`[data-suggestion-id="${suggestion.id}"]`);
            if (element) {
                element.classList.add('rejected');
                this.disableSuggestionActions(element);
            }

            this.updateStatistics();
        }
    },

    // 设置建议状态
    setSuggestionStatus: function(suggestionId, status) {
        const element = document.querySelector(`[data-suggestion-id="${suggestionId}"]`);
        if (element) {
            element.className = `fix-suggestion-card ${status}`;

            // 更新状态指示器
            const statusIcon = element.querySelector('.status-icon');
            if (statusIcon) {
                const iconMap = {
                    'pending': 'fa-clock',
                    'processing': 'fa-spinner fa-spin',
                    'completed': 'fa-check-circle',
                    'failed': 'fa-times-circle'
                };

                statusIcon.className = `fas ${iconMap[status] || 'fa-clock'}`;
            }

            // 禁用/启用操作按钮
            if (status === 'processing') {
                this.disableSuggestionActions(element);
            } else if (status === 'completed' || status === 'failed') {
                this.disableSuggestionActions(element);
            }
        }
    },

    // 禁用建议操作按钮
    disableSuggestionActions: function(element) {
        const buttons = element.querySelectorAll('.action-buttons-section button');
        buttons.forEach(btn => btn.disabled = true);
    },

    // 复制到剪贴板
    copyToClipboard: async function(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showSuccess('已复制到剪贴板');
        } catch (error) {
            console.error('Error copying to clipboard:', error);
            this.showError('复制失败');
        }
    },

    // 高亮问题行
    highlightProblemLine: function(element, suggestion) {
        const originalCode = element.querySelector('.original-code');
        if (originalCode && suggestion.line_number) {
            const lines = originalCode.textContent.split('\n');
            const targetLine = parseInt(suggestion.line_number);

            if (targetLine > 0 && targetLine <= lines.length) {
                // 创建高亮效果
                const highlightedText = lines.map((line, index) => {
                    if (index + 1 === targetLine) {
                        return `<span class="highlight-line">${line}</span>`;
                    }
                    return line;
                }).join('\n');

                originalCode.innerHTML = highlightedText;

                // 滚动到问题行
                originalCode.scrollIntoView({ behavior: 'smooth', block: 'center' });

                // 移除高亮效果
                setTimeout(() => {
                    originalCode.textContent = suggestion.original_code || '';
                }, 2000);
            }
        }
    },

    // 预览修复效果
    previewFix: function(suggestion) {
        // 显示修复前后对比
        this.showDiffModal(suggestion);
    },

    // 显示差异模态框
    showDiffModal: function(suggestion) {
        // 创建模态框
        const modalHtml = `
            <div class="modal fade" id="diffModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-exchange-alt me-2"></i>
                                修复预览
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6 class="text-danger">修复前</h6>
                                    <pre class="bg-light p-3 rounded"><code>${this.escapeHtml(suggestion.original_code || '')}</code></pre>
                                </div>
                                <div class="col-md-6">
                                    <h6 class="text-success">修复后</h6>
                                    <pre class="bg-light p-3 rounded"><code>${this.escapeHtml(suggestion.fixed_code || '')}</code></pre>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                            <button type="button" class="btn btn-primary" onclick="FixModeManager.acceptSuggestion(FixModeManager.state.fixSuggestions.find(s => s.id === '${suggestion.id}'))">
                                <i class="fas fa-check me-2"></i>应用修复
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 移除现有模态框
        const existingModal = document.getElementById('diffModal');
        if (existingModal) {
            existingModal.remove();
        }

        // 添加新模态框
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('diffModal'));
        modal.show();
    },

    // 切换批量模式
    toggleBatchMode: function() {
        this.state.batchMode = !this.state.batchMode;

        if (this.state.batchMode) {
            this.showBatchMode();
        } else {
            this.hideBatchMode();
        }
    },

    // 显示批量模式
    showBatchMode: function() {
        // 创建批量修复界面
        this.createBatchInterface();
    },

    // 创建批量修复界面
    createBatchInterface: function() {
        if (!this.elements.suggestionsContainer) return;

        const batchTemplate = document.getElementById('batchFixSuggestionTemplate');
        if (!batchTemplate) return;

        const clone = batchTemplate.content.cloneNode(true);
        const batchCard = clone.querySelector('.batch-fix-card');

        // 设置批量操作事件
        this.bindBatchEvents(batchCard);

        // 添加到容器顶部
        this.elements.suggestionsContainer.insertBefore(batchCard, this.elements.suggestionsContainer.firstChild);
    },

    // 绑定批量操作事件
    bindBatchEvents: function(batchCard) {
        // 策略选择
        const strategyRadios = batchCard.querySelectorAll('input[name="strategy"]');
        strategyRadios.forEach(radio => {
            radio.addEventListener('change', () => this.updateBatchStrategy(radio.value));
        });

        // 批量操作按钮
        const applyAllBtn = batchCard.querySelector('.apply-all-btn');
        const applySelectedBtn = batchCard.querySelector('.apply-selected-btn');
        const previewAllBtn = batchCard.querySelector('.preview-all-btn');
        const testAllBtn = batchCard.querySelector('.test-all-btn');
        const backupBtn = batchCard.querySelector('.backup-btn');

        if (applyAllBtn) {
            applyAllBtn.addEventListener('click', () => this.applyAllFixes());
        }

        if (applySelectedBtn) {
            applySelectedBtn.addEventListener('click', () => this.applySelectedFixes());
        }

        if (previewAllBtn) {
            previewAllBtn.addEventListener('click', () => this.previewAllFixes());
        }

        if (testAllBtn) {
            testAllBtn.addEventListener('click', () => this.testAllFixes());
        }

        if (backupBtn) {
            backupBtn.addEventListener('click', () => this.createBackup());
        }
    },

    // 更新批量策略
    updateBatchStrategy: function(strategy) {
        console.log('更新批量策略:', strategy);
        // 实现策略更新逻辑
    },

    // 全选建议
    selectAllSuggestions: function() {
        this.state.selectedSuggestions = [...this.state.fixSuggestions];
        this.updateSelectionUI();
    },

    // 应用所有修复
    applyAllFixes: async function() {
        if (!confirm('确定要应用所有修复建议吗？此操作将修改文件内容。')) {
            return;
        }

        if (this.state.isProcessing) {
            this.showWarning('修复正在进行中，请稍候...');
            return;
        }

        this.state.isProcessing = true;
        this.showProgress();

        try {
            const response = await fetch('/api/fix/batch-apply', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    task_id: this.state.currentTaskId,
                    suggestions: this.state.fixSuggestions,
                    strategy: 'conservative'
                })
            });

            const data = await response.json();

            if (data.success) {
                await this.processBatchResults(data.results);
                this.showSuccess('批量修复完成');
            } else {
                this.showError('批量修复失败: ' + data.error);
            }
        } catch (error) {
            console.error('Error in batch apply:', error);
            this.showError('批量修复时发生错误');
        } finally {
            this.state.isProcessing = false;
            this.hideProgress();
        }
    },

    // 应用选中的修复
    applySelectedFixes: async function() {
        if (this.state.selectedSuggestions.length === 0) {
            this.showWarning('请先选择要应用的修复建议');
            return;
        }

        if (!confirm(`确定要应用 ${this.state.selectedSuggestions.length} 个选中的修复建议吗？`)) {
            return;
        }

        this.state.isProcessing = true;
        this.showProgress();

        try {
            const response = await fetch('/api/fix/batch-apply', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    task_id: this.state.currentTaskId,
                    suggestions: this.state.selectedSuggestions,
                    strategy: 'conservative'
                })
            });

            const data = await response.json();

            if (data.success) {
                await this.processBatchResults(data.results);
                this.showSuccess('选中修复应用完成');
            } else {
                this.showError('修复应用失败: ' + data.error);
            }
        } catch (error) {
            console.error('Error applying selected fixes:', error);
            this.showError('应用修复时发生错误');
        } finally {
            this.state.isProcessing = false;
            this.hideProgress();
        }
    },

    // 处理批量修复结果
    processBatchResults: async function(results) {
        for (const result of results) {
            if (result.success) {
                this.state.appliedSuggestions.push(result.suggestion);
                this.setSuggestionStatus(result.suggestion.id, 'completed');
            } else {
                this.setSuggestionStatus(result.suggestion.id, 'failed');
            }
        }

        this.updateStatistics();
    },

    // 预览所有修复
    previewAllFixes: function() {
        const previewData = this.state.fixSuggestions.map(suggestion => ({
            id: suggestion.id,
            title: suggestion.title,
            file_path: suggestion.file_path,
            line_number: suggestion.line_number,
            severity: suggestion.severity,
            original_code: suggestion.original_code,
            fixed_code: suggestion.fixed_code
        }));

        this.showBatchPreview(previewData);
    },

    // 显示批量预览
    showBatchPreview: function(previewData) {
        // 创建预览模态框
        const modalHtml = `
            <div class="modal fade" id="batchPreviewModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-eye me-2"></i>
                                批量修复预览
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="batch-preview-container">
                                <!-- 预览内容将在这里动态生成 -->
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                            <button type="button" class="btn btn-primary" onclick="FixModeManager.applyAllFixes()">
                                <i class="fas fa-check me-2"></i>应用所有修复
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 移除现有模态框
        const existingModal = document.getElementById('batchPreviewModal');
        if (existingModal) {
            existingModal.remove();
        }

        // 添加新模态框
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // 生成预览内容
        this.generateBatchPreviewContent(previewData);

        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('batchPreviewModal'));
        modal.show();
    },

    // 生成批量预览内容
    generateBatchPreviewContent: function(previewData) {
        const container = document.querySelector('#batchPreviewModal .batch-preview-container');
        if (!container) return;

        let html = '<div class="preview-summary">';
        html += `<p class="mb-3">将要应用 <strong>${previewData.length}</strong> 个修复建议</p>`;

        const severityCount = this.countBySeverity(previewData);
        html += '<div class="severity-stats mb-3">';
        html += `<span class="badge bg-danger me-2">严重: ${severityCount.critical}</span>`;
        html += `<span class="badge bg-warning me-2">警告: ${severityCount.warning}</span>`;
        html += `<span class="badge bg-info">信息: ${severityCount.info}</span>`;
        html += '</div>';
        html += '</div>';

        html += '<div class="preview-details">';
        previewData.forEach((suggestion, index) => {
            html += `
                <div class="preview-item mb-3 p-3 border rounded">
                    <h6 class="mb-2">
                        <span class="badge bg-secondary me-2">${index + 1}</span>
                        ${suggestion.title}
                    </h6>
                    <div class="row">
                        <div class="col-md-6">
                            <small class="text-muted">文件: ${suggestion.file_path}:${suggestion.line_number}</small>
                        </div>
                        <div class="col-md-6 text-end">
                            <small class="text-muted">风险: ${this.getRiskText(suggestion.risk_level || 'medium')}</small>
                        </div>
                    </div>
                    <div class="row mt-2">
                        <div class="col-md-6">
                            <small class="text-danger">修改前:</small>
                            <pre class="bg-light p-2 rounded small">${this.escapeHtml(suggestion.original_code || '')}</pre>
                        </div>
                        <div class="col-md-6">
                            <small class="text-success">修改后:</small>
                            <pre class="bg-light p-2 rounded small">${this.escapeHtml(suggestion.fixed_code || '')}</pre>
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';

        container.innerHTML = html;
    },

    // 测试所有修复
    testAllFixes: async function() {
        this.showInfo('正在运行测试...');

        try {
            const response = await fetch('/api/fix/test-all', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    task_id: this.state.currentTaskId,
                    suggestions: this.state.appliedSuggestions
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showTestResults(data.results);
            } else {
                this.showError('测试失败: ' + data.error);
            }
        } catch (error) {
            console.error('Error running tests:', error);
            this.showError('测试时发生错误');
        }
    },

    // 显示测试结果
    showTestResults: function(results) {
        const passed = results.filter(r => r.passed).length;
        const failed = results.filter(r => !r.passed).length;

        if (failed === 0) {
            this.showSuccess(`所有测试通过 (${passed}/${results.length})`);
        } else {
            this.showWarning(`部分测试失败 (${passed}/${results.length} 通过, ${failed} 失败)`);
        }
    },

    // 创建备份
    createBackup: async function() {
        try {
            const response = await fetch('/api/fix/backup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    task_id: this.state.currentTaskId
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('备份创建成功');
            } else {
                this.showError('备份创建失败: ' + data.error);
            }
        } catch (error) {
            console.error('Error creating backup:', error);
            this.showError('创建备份时发生错误');
        }
    },

    // 取消操作
    cancelOperation: function() {
        if (this.state.isProcessing) {
            if (confirm('确定要取消当前操作吗？')) {
                this.state.isProcessing = false;
                this.hideProgress();
                this.showInfo('操作已取消');
            }
        }
    },

    // 处理修复建议点击事件
    handleSuggestionClick: function(event) {
        const suggestionElement = event.target.closest('.fix-suggestion-card');
        if (!suggestionElement) return;

        const suggestionId = suggestionElement.dataset.suggestionId;
        const suggestion = this.state.fixSuggestions.find(s => s.id === suggestionId);

        if (!suggestion) return;

        // 处理选择框点击
        if (event.target.matches('input[type="checkbox"]')) {
            this.handleSelectionChange(suggestion, event.target.checked);
        }
    },

    // 处理选择变化
    handleSelectionChange: function(suggestion, checked) {
        if (checked) {
            if (!this.state.selectedSuggestions.find(s => s.id === suggestion.id)) {
                this.state.selectedSuggestions.push(suggestion);
            }
        } else {
            this.state.selectedSuggestions = this.state.selectedSuggestions.filter(s => s.id !== suggestion.id);
        }

        this.updateSelectionUI();
    },

    // 更新选择UI
    updateSelectionUI: function() {
        // 更新全选按钮状态
        if (this.elements.selectAllBtn) {
            this.elements.selectAllBtn.textContent =
                this.state.selectedSuggestions.length === this.state.fixSuggestions.length ? '取消全选' : '全选';
        }

        // 更新批量操作按钮状态
        if (this.elements.applySelectedBtn) {
            this.elements.applySelectedBtn.disabled = this.state.selectedSuggestions.length === 0;
        }

        // 更新选择框状态
        this.state.fixSuggestions.forEach(suggestion => {
            const element = document.querySelector(`[data-suggestion-id="${suggestion.id}"]`);
            if (element) {
                const checkbox = element.querySelector('input[type="checkbox"]');
                if (checkbox) {
                    checkbox.checked = this.state.selectedSuggestions.find(sel => sel.id === suggestion.id) !== undefined;
                }
            }
        });

        // 更新统计
        this.updateStatistics();
    },

    // 显示进度
    showProgress: function() {
        if (this.elements.progressContainer) {
            this.elements.progressContainer.style.display = 'block';
        }

        if (this.elements.progressBar) {
            this.elements.progressBar.style.width = '0%';
        }

        if (this.elements.progressText) {
            this.elements.progressText.textContent = '正在准备...';
        }
    },

    // 隐藏进度
    hideProgress: function() {
        if (this.elements.progressContainer) {
            this.elements.progressContainer.style.display = 'none';
        }
    },

    // 更新进度
    updateProgress: function(percentage, text) {
        if (this.elements.progressBar) {
            this.elements.progressBar.style.width = `${percentage}%`;
        }

        if (this.elements.progressText) {
            this.elements.progressText.textContent = text || '';
        }
    },

    // 更新统计信息
    updateStatistics: function() {
        const total = this.state.fixSuggestions.length;
        const applied = this.state.appliedSuggestions.length;
        const remaining = total - applied;

        if (this.elements.totalIssues) {
            this.elements.totalIssues.textContent = total;
        }

        if (this.elements.fixedIssues) {
            this.elements.fixedIssues.textContent = applied;
        }

        if (this.elements.remainingIssues) {
            this.elements.remainingIssues.textContent = remaining;
        }

        if (this.elements.successRate) {
            const rate = total > 0 ? Math.round((applied / total) * 100) : 0;
            this.elements.successRate.textContent = `${rate}%`;
        }
    },

    // 显示消息
    showLoading: function(message) {
        this.showMessage(message, 'info');
    },

    showSuccess: function(message) {
        this.showMessage(message, 'success');
    },

    showError: function(message) {
        this.showMessage(message, 'danger');
    },

    showWarning: function(message) {
        this.showMessage(message, 'warning');
    },

    showInfo: function(message) {
        this.showMessage(message, 'info');
    },

    showMessage: function(message, type) {
        // 创建消息元素
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // 添加到页面顶部
        const container = document.querySelector('.container-fluid, .fix-container');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
        }

        // 3秒后自动消失
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 3000);
    },

    // 辅助函数
    getSeverityText: function(severity) {
        const map = {
            'critical': '严重',
            'warning': '警告',
            'info': '信息'
        };
        return map[severity] || severity;
    },

    getRiskText: function(risk) {
        const map = {
            'low': '低风险',
            'medium': '中风险',
            'high': '高风险'
        };
        return map[risk] || risk;
    },

    getRiskPercentage: function(risk) {
        const map = {
            'low': 25,
            'medium': 50,
            'high': 75
        };
        return map[risk] || 50;
    },

    getRiskNumericValue: function(risk) {
        const map = {
            'low': 2,
            'medium': 5,
            'high': 8
        };
        return map[risk] || 5;
    },

    getRiskLevel: function(value) {
        if (value <= 3) return 'low';
        if (value <= 7) return 'medium';
        return 'high';
    },

    countBySeverity: function(suggestions) {
        return suggestions.reduce((count, s) => {
            count[s.severity] = (count[s.severity] || 0) + 1;
            return count;
        }, {});
    },

    escapeHtml: function(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 设置当前页面
    App.Sidebar.setActive('fix');

    // 初始化修复模式管理器
    FixModeManager.init();
});
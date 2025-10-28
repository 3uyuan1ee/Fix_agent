/**
 * 历史记录页面JavaScript逻辑
 * 包含记录加载、搜索筛选、详情展示、删除导出等功能
 */

class HistoryManager {
    constructor() {
        this.records = [];
        this.filteredRecords = [];
        this.currentPage = 1;
        this.pageSize = 10;
        this.selectedRecords = new Set();
        this.sortBy = 'created_at_desc';
        this.filters = {
            search: '',
            type: '',
            status: '',
            dateRange: ''
        };

        this.initializeElements();
        this.bindEvents();
        this.loadRecords();
    }

    initializeElements() {
        // 表单元素
        this.filterForm = document.getElementById('filterForm');
        this.searchInput = document.getElementById('searchInput');
        this.typeFilter = document.getElementById('typeFilter');
        this.statusFilter = document.getElementById('statusFilter');
        this.dateFilter = document.getElementById('dateFilter');
        this.sortBySelect = document.getElementById('sortBy');

        // 统计元素
        this.totalCount = document.getElementById('totalCount');
        this.completedCount = document.getElementById('completedCount');
        this.runningCount = document.getElementById('runningCount');
        this.failedCount = document.getElementById('failedCount');

        // 表格元素
        this.loadingState = document.getElementById('loadingState');
        this.emptyState = document.getElementById('emptyState');
        this.recordsTable = document.getElementById('recordsTable');
        this.recordsTableBody = document.getElementById('recordsTableBody');
        this.selectAllCheckbox = document.getElementById('selectAll');

        // 分页元素
        this.pagination = document.getElementById('pagination');

        // 模态框元素
        this.recordDetailModal = new bootstrap.Modal(document.getElementById('recordDetailModal'));
        this.confirmDeleteModal = new bootstrap.Modal(document.getElementById('confirmDeleteModal'));
        this.recordDetailContent = document.getElementById('recordDetailContent');

        // 按钮
        this.exportBtn = document.getElementById('exportBtn');
        this.clearAllBtn = document.getElementById('clearAllBtn');
        this.confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
        this.exportRecordBtn = document.getElementById('exportRecordBtn');
    }

    bindEvents() {
        // 搜索和筛选事件
        this.searchInput.addEventListener('input', this.debounce(() => {
            this.filters.search = this.searchInput.value.trim();
            this.currentPage = 1;
            this.applyFilters();
        }, 300));

        this.typeFilter.addEventListener('change', () => {
            this.filters.type = this.typeFilter.value;
            this.currentPage = 1;
            this.applyFilters();
        });

        this.statusFilter.addEventListener('change', () => {
            this.filters.status = this.statusFilter.value;
            this.currentPage = 1;
            this.applyFilters();
        });

        this.dateFilter.addEventListener('change', () => {
            this.filters.dateRange = this.dateFilter.value;
            this.currentPage = 1;
            this.applyFilters();
        });

        this.sortBySelect.addEventListener('change', () => {
            this.sortBy = this.sortBySelect.value;
            this.applyFilters();
        });

        // 全选事件
        this.selectAllCheckbox.addEventListener('change', () => {
            this.selectAllRecords(this.selectAllCheckbox.checked);
        });

        // 按钮事件
        this.exportBtn.addEventListener('click', () => this.exportRecords());
        this.clearAllBtn.addEventListener('click', () => this.clearAllRecords());
        this.confirmDeleteBtn.addEventListener('click', () => this.deleteSelectedRecords());
        this.exportRecordBtn.addEventListener('click', () => this.exportCurrentRecord());

        // 表单提交阻止
        this.filterForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.applyFilters();
        });

        // 模态框事件
        document.getElementById('recordDetailModal').addEventListener('hidden.bs.modal', () => {
            this.recordDetailContent.innerHTML = '';
        });
    }

    async loadRecords() {
        try {
            this.showLoading();
            const response = await fetch('/api/history/records');

            if (!response.ok) {
                throw new Error('获取历史记录失败');
            }

            const data = await response.json();
            this.records = data.records || [];
            this.applyFilters();
            this.updateStats();

        } catch (error) {
            console.error('加载历史记录失败:', error);
            this.showError('加载历史记录失败，请刷新页面重试');
        }
    }

    applyFilters() {
        let filtered = [...this.records];

        // 应用搜索过滤
        if (this.filters.search) {
            const searchTerm = this.filters.search.toLowerCase();
            filtered = filtered.filter(record =>
                record.project_name?.toLowerCase().includes(searchTerm) ||
                record.file_path?.toLowerCase().includes(searchTerm) ||
                record.description?.toLowerCase().includes(searchTerm)
            );
        }

        // 应用类型过滤
        if (this.filters.type) {
            filtered = filtered.filter(record => record.analysis_type === this.filters.type);
        }

        // 应用状态过滤
        if (this.filters.status) {
            filtered = filtered.filter(record => record.status === this.filters.status);
        }

        // 应用日期范围过滤
        if (this.filters.dateRange) {
            const now = new Date();
            const startDate = this.getDateRangeStart(this.filters.dateRange, now);
            filtered = filtered.filter(record =>
                new Date(record.created_at) >= startDate
            );
        }

        // 应用排序
        filtered = this.sortRecords(filtered, this.sortBy);

        this.filteredRecords = filtered;
        this.renderTable();
        this.updatePagination();
    }

    getDateRangeStart(range, now) {
        switch (range) {
            case 'today':
                return new Date(now.getFullYear(), now.getMonth(), now.getDate());
            case 'week':
                return new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
            case 'month':
                return new Date(now.getFullYear(), now.getMonth(), 1);
            case 'year':
                return new Date(now.getFullYear(), 0, 1);
            default:
                return new Date(0);
        }
    }

    sortRecords(records, sortBy) {
        return [...records].sort((a, b) => {
            switch (sortBy) {
                case 'created_at_desc':
                    return new Date(b.created_at) - new Date(a.created_at);
                case 'created_at_asc':
                    return new Date(a.created_at) - new Date(b.created_at);
                case 'name_asc':
                    return (a.project_name || '').localeCompare(b.project_name || '');
                case 'name_desc':
                    return (b.project_name || '').localeCompare(a.project_name || '');
                default:
                    return 0;
            }
        });
    }

    renderTable() {
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const pageRecords = this.filteredRecords.slice(startIndex, endIndex);

        if (pageRecords.length === 0) {
            this.showEmpty();
            return;
        }

        this.recordsTableBody.innerHTML = '';
        pageRecords.forEach(record => {
            const row = this.createRecordRow(record);
            this.recordsTableBody.appendChild(row);
        });

        this.showTable();
    }

    createRecordRow(record) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <input type="checkbox" class="form-check-input record-checkbox"
                       data-record-id="${record.id}" ${this.selectedRecords.has(record.id) ? 'checked' : ''}>
            </td>
            <td>
                <div class="fw-bold">${this.escapeHtml(record.project_name || '未命名项目')}</div>
                <small class="text-muted">${this.escapeHtml(record.file_path || '')}</small>
            </td>
            <td>
                <span class="type-badge ${record.analysis_type}">
                    ${this.getTypeLabel(record.analysis_type)}
                </span>
            </td>
            <td>
                <span class="status-badge ${record.status}">
                    ${this.getStatusLabel(record.status)}
                </span>
            </td>
            <td>${record.file_count || 0}</td>
            <td>${record.issue_count || 0}</td>
            <td>
                <small>${this.formatDate(record.created_at)}</small>
            </td>
            <td>
                <small>${this.formatDuration(record.duration)}</small>
            </td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-sm btn-outline-primary view-btn" data-record-id="${record.id}">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-success export-btn" data-record-id="${record.id}">
                        <i class="fas fa-download"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger delete-btn" data-record-id="${record.id}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;

        // 绑定行内按钮事件
        row.querySelector('.view-btn').addEventListener('click', () => this.viewRecordDetail(record.id));
        row.querySelector('.export-btn').addEventListener('click', () => this.exportRecord(record.id));
        row.querySelector('.delete-btn').addEventListener('click', () => this.deleteRecord(record.id));
        row.querySelector('.record-checkbox').addEventListener('change', (e) => {
            this.toggleRecordSelection(record.id, e.target.checked);
        });

        return row;
    }

    getTypeLabel(type) {
        const labels = {
            static: '静态分析',
            deep: '深度分析',
            fix: '修复模式'
        };
        return labels[type] || type;
    }

    getStatusLabel(status) {
        const labels = {
            completed: '已完成',
            failed: '失败',
            running: '运行中',
            pending: '等待中'
        };
        return labels[status] || status;
    }

    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    formatDuration(seconds) {
        if (!seconds) return '-';
        if (seconds < 60) return `${seconds}秒`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`;
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}小时${minutes}分`;
    }

    updateStats() {
        const stats = {
            total: this.records.length,
            completed: 0,
            running: 0,
            failed: 0
        };

        this.records.forEach(record => {
            switch (record.status) {
                case 'completed':
                    stats.completed++;
                    break;
                case 'running':
                    stats.running++;
                    break;
                case 'failed':
                    stats.failed++;
                    break;
            }
        });

        this.totalCount.textContent = stats.total;
        this.completedCount.textContent = stats.completed;
        this.runningCount.textContent = stats.running;
        this.failedCount.textContent = stats.failed;
    }

    updatePagination() {
        const totalPages = Math.ceil(this.filteredRecords.length / this.pageSize);
        this.pagination.innerHTML = '';

        if (totalPages <= 1) return;

        // 上一页
        const prevLi = document.createElement('li');
        prevLi.className = `page-item ${this.currentPage === 1 ? 'disabled' : ''}`;
        prevLi.innerHTML = `
            <a class="page-link" href="#" data-page="${this.currentPage - 1}">
                <i class="fas fa-chevron-left"></i>
            </a>
        `;
        this.pagination.appendChild(prevLi);

        // 页码
        const startPage = Math.max(1, this.currentPage - 2);
        const endPage = Math.min(totalPages, this.currentPage + 2);

        for (let i = startPage; i <= endPage; i++) {
            const pageLi = document.createElement('li');
            pageLi.className = `page-item ${i === this.currentPage ? 'active' : ''}`;
            pageLi.innerHTML = `
                <a class="page-link" href="#" data-page="${i}">${i}</a>
            `;
            this.pagination.appendChild(pageLi);
        }

        // 下一页
        const nextLi = document.createElement('li');
        nextLi.className = `page-item ${this.currentPage === totalPages ? 'disabled' : ''}`;
        nextLi.innerHTML = `
            <a class="page-link" href="#" data-page="${this.currentPage + 1}">
                <i class="fas fa-chevron-right"></i>
            </a>
        `;
        this.pagination.appendChild(nextLi);

        // 绑定分页事件
        this.pagination.addEventListener('click', (e) => {
            e.preventDefault();
            const pageLink = e.target.closest('.page-link');
            if (pageLink && !pageLink.parentElement.classList.contains('disabled')) {
                const page = parseInt(pageLink.dataset.page);
                this.goToPage(page);
            }
        });
    }

    goToPage(page) {
        this.currentPage = page;
        this.renderTable();
        this.updatePagination();
    }

    selectAllRecords(checked) {
        const checkboxes = document.querySelectorAll('.record-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.checked = checked;
            const recordId = checkbox.dataset.recordId;
            if (checked) {
                this.selectedRecords.add(recordId);
            } else {
                this.selectedRecords.delete(recordId);
            }
        });
        this.updateBatchActions();
    }

    toggleRecordSelection(recordId, checked) {
        if (checked) {
            this.selectedRecords.add(recordId);
        } else {
            this.selectedRecords.delete(recordId);
        }
        this.updateSelectAllCheckbox();
        this.updateBatchActions();
    }

    updateSelectAllCheckbox() {
        const visibleCheckboxes = document.querySelectorAll('.record-checkbox');
        const checkedCount = document.querySelectorAll('.record-checkbox:checked').length;

        if (visibleCheckboxes.length === 0) {
            this.selectAllCheckbox.checked = false;
            this.selectAllCheckbox.indeterminate = false;
        } else if (checkedCount === 0) {
            this.selectAllCheckbox.checked = false;
            this.selectAllCheckbox.indeterminate = false;
        } else if (checkedCount === visibleCheckboxes.length) {
            this.selectAllCheckbox.checked = true;
            this.selectAllCheckbox.indeterminate = false;
        } else {
            this.selectAllCheckbox.checked = false;
            this.selectAllCheckbox.indeterminate = true;
        }
    }

    updateBatchActions() {
        // 这里可以实现批量操作栏的显示/隐藏逻辑
        console.log('已选择记录数:', this.selectedRecords.size);
    }

    async viewRecordDetail(recordId) {
        try {
            const response = await fetch(`/api/history/record/${recordId}`);

            if (!response.ok) {
                throw new Error('获取记录详情失败');
            }

            const record = await response.json();
            this.renderRecordDetail(record);
            this.recordDetailModal.show();

        } catch (error) {
            console.error('获取记录详情失败:', error);
            this.showError('获取记录详情失败');
        }
    }

    renderRecordDetail(record) {
        this.currentRecord = record;

        this.recordDetailContent.innerHTML = `
            <!-- 基本信息 -->
            <div class="record-detail-section">
                <h6><i class="fas fa-info-circle"></i> 基本信息</h6>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">项目名称</span>
                        <span class="detail-value">${this.escapeHtml(record.project_name || '未命名')}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">分析类型</span>
                        <span class="detail-value">
                            <span class="type-badge ${record.analysis_type}">
                                ${this.getTypeLabel(record.analysis_type)}
                            </span>
                        </span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">状态</span>
                        <span class="detail-value">
                            <span class="status-badge ${record.status}">
                                ${this.getStatusLabel(record.status)}
                            </span>
                        </span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">创建时间</span>
                        <span class="detail-value">${this.formatDate(record.created_at)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">完成时间</span>
                        <span class="detail-value">${this.formatDate(record.completed_at)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">执行耗时</span>
                        <span class="detail-value">${this.formatDuration(record.duration)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">文件数量</span>
                        <span class="detail-value">${record.file_count || 0}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">问题数量</span>
                        <span class="detail-value">${record.issue_count || 0}</span>
                    </div>
                </div>
            </div>

            <!-- 文件列表 -->
            <div class="record-detail-section">
                <h6><i class="fas fa-file-code"></i> 分析文件</h6>
                <div class="file-list">
                    ${this.renderFileList(record.files || [])}
                </div>
            </div>

            <!-- 问题列表 -->
            ${record.issues && record.issues.length > 0 ? `
                <div class="record-detail-section">
                    <h6><i class="fas fa-exclamation-triangle"></i> 发现问题</h6>
                    <div class="issue-list">
                        ${this.renderIssueList(record.issues)}
                    </div>
                </div>
            ` : ''}

            <!-- 配置信息 -->
            <div class="record-detail-section">
                <h6><i class="fas fa-cog"></i> 分析配置</h6>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">分析工具</span>
                        <span class="detail-value">${this.escapeHtml(record.tools?.join(', ') || 'N/A')}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">模型名称</span>
                        <span class="detail-value">${this.escapeHtml(record.model_name || 'N/A')}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">API提供商</span>
                        <span class="detail-value">${this.escapeHtml(record.provider || 'N/A')}</span>
                    </div>
                </div>
            </div>
        `;
    }

    renderFileList(files) {
        if (!files || files.length === 0) {
            return '<div class="text-center text-muted p-3">无文件记录</div>';
        }

        return files.map(file => `
            <div class="file-item">
                <div class="file-path" title="${this.escapeHtml(file.path)}">
                    ${this.escapeHtml(file.path)}
                </div>
                <div class="file-stats">
                    <span>${file.size || 'N/A'}</span>
                    <span>${file.lines || 'N/A'} 行</span>
                    <span>${file.issues || 0} 问题</span>
                </div>
            </div>
        `).join('');
    }

    renderIssueList(issues) {
        if (!issues || issues.length === 0) {
            return '<div class="text-center text-muted p-3">无问题记录</div>';
        }

        return issues.slice(0, 20).map(issue => `
            <div class="issue-item">
                <div class="issue-header">
                    <div class="issue-title">${this.escapeHtml(issue.title || '未命名问题')}</div>
                    <span class="issue-severity severity-${issue.severity || 'info'}">
                        ${issue.severity || 'info'}
                    </span>
                </div>
                <div class="issue-description">${this.escapeHtml(issue.description || '')}</div>
                <div class="issue-location">
                    <i class="fas fa-map-marker-alt me-1"></i>
                    ${this.escapeHtml(issue.file_path || '')}:${issue.line_number || '?'}
                </div>
            </div>
        `).join('');
    }

    async exportRecord(recordId) {
        try {
            const response = await fetch(`/api/history/record/${recordId}/export`);

            if (!response.ok) {
                throw new Error('导出记录失败');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `record_${recordId}_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            this.showSuccess('记录导出成功');

        } catch (error) {
            console.error('导出记录失败:', error);
            this.showError('导出记录失败');
        }
    }

    async deleteRecord(recordId) {
        if (!confirm('确定要删除这条记录吗？此操作不可撤销。')) {
            return;
        }

        try {
            const response = await fetch(`/api/history/record/${recordId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('删除记录失败');
            }

            this.records = this.records.filter(r => r.id !== recordId);
            this.selectedRecords.delete(recordId);
            this.applyFilters();
            this.updateStats();
            this.showSuccess('记录删除成功');

        } catch (error) {
            console.error('删除记录失败:', error);
            this.showError('删除记录失败');
        }
    }

    async exportRecords() {
        try {
            const recordIds = Array.from(this.selectedRecords);
            if (recordIds.length === 0) {
                this.showError('请先选择要导出的记录');
                return;
            }

            const response = await fetch('/api/history/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ record_ids: recordIds })
            });

            if (!response.ok) {
                throw new Error('批量导出失败');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `history_export_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            this.showSuccess('记录导出成功');

        } catch (error) {
            console.error('批量导出失败:', error);
            this.showError('批量导出失败');
        }
    }

    async clearAllRecords() {
        if (!confirm('确定要清空所有历史记录吗？此操作不可撤销，将删除所有分析记录。')) {
            return;
        }

        try {
            const response = await fetch('/api/history/clear', {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('清空记录失败');
            }

            this.records = [];
            this.selectedRecords.clear();
            this.applyFilters();
            this.updateStats();
            this.showSuccess('所有记录已清空');

        } catch (error) {
            console.error('清空记录失败:', error);
            this.showError('清空记录失败');
        }
    }

    async deleteSelectedRecords() {
        const recordIds = Array.from(this.selectedRecords);
        if (recordIds.length === 0) {
            this.showError('请先选择要删除的记录');
            return;
        }

        try {
            const response = await fetch('/api/history/batch-delete', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ record_ids: recordIds })
            });

            if (!response.ok) {
                throw new Error('批量删除失败');
            }

            this.records = this.records.filter(r => !recordIds.includes(r.id));
            this.selectedRecords.clear();
            this.applyFilters();
            this.updateStats();
            this.confirmDeleteModal.hide();
            this.showSuccess('选中记录删除成功');

        } catch (error) {
            console.error('批量删除失败:', error);
            this.showError('批量删除失败');
        }
    }

    exportCurrentRecord() {
        if (this.currentRecord) {
            this.exportRecord(this.currentRecord.id);
        }
    }

    showLoading() {
        this.loadingState.classList.remove('d-none');
        this.emptyState.classList.add('d-none');
        this.recordsTable.classList.add('d-none');
    }

    showEmpty() {
        this.loadingState.classList.add('d-none');
        this.emptyState.classList.remove('d-none');
        this.recordsTable.classList.add('d-none');
    }

    showTable() {
        this.loadingState.classList.add('d-none');
        this.emptyState.classList.add('d-none');
        this.recordsTable.classList.remove('d-none');
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'danger');
    }

    showNotification(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        const container = document.createElement('div');
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.appendChild(toast);
        document.body.appendChild(container);

        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => {
            container.remove();
        });
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

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
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    new HistoryManager();
});
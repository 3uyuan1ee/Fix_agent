/**
 * 代码对比查看器组件
 * 提供专业的代码差异显示功能
 */

class DiffViewer {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            showLineNumbers: true,
            highlightSyntax: true,
            contextLines: 3,
            ...options
        };
        this.originalCode = '';
        this.fixedCode = '';
    }

    /**
     * 设置原始代码和修复后代码
     */
    setCodes(originalCode, fixedCode) {
        this.originalCode = originalCode;
        this.fixedCode = fixedCode;
    }

    /**
     * 渲染代码对比
     */
    render() {
        if (!this.container) {
            console.error('DiffViewer container not found');
            return;
        }

        const diffResult = this.generateDiff();
        const html = this.renderDiffHtml(diffResult);
        this.container.innerHTML = html;
    }

    /**
     * 生成代码差异
     */
    generateDiff() {
        const originalLines = this.originalCode.split('\n');
        const fixedLines = this.fixedCode.split('\n');

        return this.computeLCS(originalLines, fixedLines);
    }

    /**
     * 使用最长公共子序列算法计算差异
     */
    computeLCS(originalLines, fixedLines) {
        const m = originalLines.length;
        const n = fixedLines.length;

        // 创建DP表
        const dp = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));

        // 填充DP表
        for (let i = 1; i <= m; i++) {
            for (let j = 1; j <= n; j++) {
                if (originalLines[i - 1] === fixedLines[j - 1]) {
                    dp[i][j] = dp[i - 1][j - 1] + 1;
                } else {
                    dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
                }
            }
        }

        // 回溯生成差异结果
        const diffResult = [];
        let i = m, j = n;

        while (i > 0 || j > 0) {
            if (i > 0 && j > 0 && originalLines[i - 1] === fixedLines[j - 1]) {
                diffResult.unshift({
                    type: 'unchanged',
                    originalLine: i,
                    fixedLine: j,
                    content: originalLines[i - 1]
                });
                i--;
                j--;
            } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
                diffResult.unshift({
                    type: 'added',
                    originalLine: null,
                    fixedLine: j,
                    content: fixedLines[j - 1]
                });
                j--;
            } else if (i > 0) {
                diffResult.unshift({
                    type: 'removed',
                    originalLine: i,
                    fixedLine: null,
                    content: originalLines[i - 1]
                });
                i--;
            }
        }

        return diffResult;
    }

    /**
     * 渲染差异HTML
     */
    renderDiffHtml(diffResult) {
        let html = '<div class="diff-container">';

        // 添加表头
        html += `
            <div class="diff-header">
                <div class="row">
                    <div class="col-6 text-center">
                        <span class="diff-title text-danger">
                            <i class="fas fa-times-circle me-1"></i>修复前
                        </span>
                    </div>
                    <div class="col-6 text-center">
                        <span class="diff-title text-success">
                            <i class="fas fa-check-circle me-1"></i>修复后
                        </span>
                    </div>
                </div>
            </div>
        `;

        // 添加代码行
        html += '<div class="diff-content">';
        html += '<div class="row">';

        // 原始代码列
        html += '<div class="col-6 diff-column">';
        html += this.renderCodeColumn(diffResult, 'original');
        html += '</div>';

        // 修复后代码列
        html += '<div class="col-6 diff-column">';
        html += this.renderCodeColumn(diffResult, 'fixed');
        html += '</div>';

        html += '</div>';
        html += '</div>';
        html += '</div>';

        return html;
    }

    /**
     * 渲染单列代码
     */
    renderCodeColumn(diffResult, columnType) {
        let html = '<div class="code-lines">';

        diffResult.forEach((diff, index) => {
            const shouldRender = this.shouldRenderLine(diff, columnType);
            if (!shouldRender) return;

            const lineNumber = columnType === 'original' ? diff.originalLine : diff.fixedLine;
            const lineType = diff.type;

            html += this.renderLine(lineNumber, diff.content, lineType, index);
        });

        html += '</div>';
        return html;
    }

    /**
     * 判断是否应该渲染该行
     */
    shouldRenderLine(diff, columnType) {
        if (diff.type === 'unchanged') {
            return true;
        }

        if (columnType === 'original' && diff.type === 'removed') {
            return true;
        }

        if (columnType === 'fixed' && diff.type === 'added') {
            return true;
        }

        return false;
    }

    /**
     * 渲染单行代码
     */
    renderLine(lineNumber, content, type, index) {
        const lineClass = `diff-line ${type}`;
        const lineContent = this.escapeHtml(content) || ' ';

        let html = `<div class="${lineClass}" data-line="${lineNumber}" data-index="${index}">`;

        if (this.options.showLineNumbers && lineNumber) {
            html += `<span class="line-number">${lineNumber}</span>`;
        } else if (this.options.showLineNumbers) {
            html += `<span class="line-number empty"></span>`;
        }

        html += `<span class="code-content">${lineContent}</span>`;
        html += '</div>';

        return html;
    }

    /**
     * HTML转义
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    /**
     * 添加语法高亮
     */
    highlightSyntax(code) {
        if (!this.options.highlightSyntax) return code;

        // 简单的关键词高亮
        const keywords = ['function', 'var', 'let', 'const', 'if', 'else', 'for', 'while', 'return', 'class', 'import', 'export'];
        const regex = new RegExp(`\\b(${keywords.join('|')})\\b`, 'g');

        return code.replace(regex, '<span class="keyword">$1</span>');
    }

    /**
     * 获取统计信息
     */
    getStatistics() {
        const diffResult = this.generateDiff();
        const stats = {
            added: 0,
            removed: 0,
            unchanged: 0
        };

        diffResult.forEach(diff => {
            stats[diff.type]++;
        });

        return stats;
    }

    /**
     * 添加行号点击事件
     */
    addLineClickHandler(callback) {
        if (!this.container) return;

        this.container.addEventListener('click', (event) => {
            const lineElement = event.target.closest('.diff-line');
            if (lineElement) {
                const lineNumber = lineElement.dataset.line;
                const index = lineElement.dataset.index;
                const type = Array.from(lineElement.classList).find(c =>
                    ['added', 'removed', 'unchanged'].includes(c)
                );

                callback({
                    lineNumber: parseInt(lineNumber),
                    index: parseInt(index),
                    type: type,
                    element: lineElement
                });
            }
        });
    }

    /**
     * 高亮特定行
     */
    highlightLine(lineIndex, className = 'highlighted') {
        if (!this.container) return;

        const lines = this.container.querySelectorAll('.diff-line');
        lines.forEach(line => line.classList.remove(className));

        const targetLine = this.container.querySelector(`.diff-line[data-index="${lineIndex}"]`);
        if (targetLine) {
            targetLine.classList.add(className);
            targetLine.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    /**
     * 切换差异显示模式
     */
    toggleViewMode(mode) {
        // 可以实现不同的显示模式，如并排对比、统一对比等
        console.log('Switching to view mode:', mode);
        // TODO: 实现不同的视图模式
    }

    /**
     * 导出差异结果
     */
    exportDiff(format = 'text') {
        const diffResult = this.generateDiff();

        switch (format) {
            case 'text':
                return this.exportAsText(diffResult);
            case 'json':
                return this.exportAsJson(diffResult);
            case 'html':
                return this.exportAsHtml(diffResult);
            default:
                throw new Error(`Unsupported export format: ${format}`);
        }
    }

    /**
     * 导出为文本格式
     */
    exportAsText(diffResult) {
        let text = '';

        diffResult.forEach(diff => {
            const prefix = diff.type === 'added' ? '+' :
                          diff.type === 'removed' ? '-' : ' ';
            text += `${prefix} ${diff.content}\n`;
        });

        return text;
    }

    /**
     * 导出为JSON格式
     */
    exportAsJson(diffResult) {
        return JSON.stringify(diffResult, null, 2);
    }

    /**
     * 导出为HTML格式
     */
    exportAsHtml(diffResult) {
        const stats = this.getStatistics();
        let html = `
            <div class="diff-export">
                <div class="diff-stats">
                    <p>添加: ${stats.added} 行</p>
                    <p>删除: ${stats.removed} 行</p>
                    <p>未变更: ${stats.unchanged} 行</p>
                </div>
                <div class="diff-content">
                    ${this.renderDiffHtml(diffResult)}
                </div>
            </div>
        `;

        return html;
    }
}

// 简化的diff算法，适用于较小的代码文件
class SimpleDiffViewer extends DiffViewer {
    generateDiff() {
        const originalLines = this.originalCode.split('\n');
        const fixedLines = this.fixedCode.split('\n');

        const result = [];
        let i = 0, j = 0;

        while (i < originalLines.length || j < fixedLines.length) {
            if (i < originalLines.length && j < fixedLines.length) {
                if (originalLines[i] === fixedLines[j]) {
                    result.push({
                        type: 'unchanged',
                        originalLine: i + 1,
                        fixedLine: j + 1,
                        content: originalLines[i]
                    });
                    i++;
                    j++;
                } else {
                    // 简单处理：先删除后添加
                    if (i < originalLines.length) {
                        result.push({
                            type: 'removed',
                            originalLine: i + 1,
                            fixedLine: null,
                            content: originalLines[i]
                        });
                        i++;
                    }
                    if (j < fixedLines.length) {
                        result.push({
                            type: 'added',
                            originalLine: null,
                            fixedLine: j + 1,
                            content: fixedLines[j]
                        });
                        j++;
                    }
                }
            } else if (i < originalLines.length) {
                result.push({
                    type: 'removed',
                    originalLine: i + 1,
                    fixedLine: null,
                    content: originalLines[i]
                });
                i++;
            } else if (j < fixedLines.length) {
                result.push({
                    type: 'added',
                    originalLine: null,
                    fixedLine: j + 1,
                    content: fixedLines[j]
                });
                j++;
            }
        }

        return result;
    }
}

// 全局函数，用于在fix.html中调用
function createDiffViewer(containerId, options = {}) {
    return new DiffViewer(containerId, options);
}

function createSimpleDiffViewer(containerId, options = {}) {
    return new SimpleDiffViewer(containerId, options);
}
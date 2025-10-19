#!/usr/bin/env python3
"""
AIDefectDetector Web界面模块
Flask Web应用基础框架
"""

import os
from pathlib import Path

# Flask相关导入
try:
    from flask import Flask, render_template, send_from_directory, jsonify, request
except ImportError:
    Flask = None
    render_template = None
    send_from_directory = None
    jsonify = None
    request = None

# 项目内部导入
from src.utils.config import get_config_manager
from src.utils.logger import get_logger


class AIDefectDetectorWeb:
    """AIDefectDetector Web应用主类"""

    def __init__(self):
        """初始化Web应用"""
        if Flask is None:
            raise ImportError("Flask未安装，请运行: pip install flask")

        self.config_manager = get_config_manager()
        self.config = self.config_manager._config
        self.logger = get_logger()
        self.app = None
        self._create_app()

    def _create_app(self):
        """创建Flask应用实例"""
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent

        # 创建Flask应用
        self.app = Flask(
            __name__,
            static_folder=str(project_root / "web" / "static"),
            template_folder=str(project_root / "web" / "templates")
        )

        # 配置应用
        self._configure_app()

        # 注册路由
        self._register_routes()

        # 注册错误处理器
        self._register_error_handlers()

        self.logger.info("Flask应用创建完成")

    def _configure_app(self):
        """配置Flask应用"""
        # 从配置系统获取Web配置
        web_config = self.config.get('web', {})

        # 基础配置
        self.app.config['SECRET_KEY'] = web_config.get('secret_key', 'dev-secret-key-change-in-production')
        self.app.config['DEBUG'] = web_config.get('debug', False)

        # 文件上传配置
        upload_folder = web_config.get('upload_folder', 'uploads')
        self.app.config['UPLOAD_FOLDER'] = upload_folder
        self.app.config['MAX_CONTENT_LENGTH'] = web_config.get('max_upload_size', 50 * 1024 * 1024)  # 50MB

        # 确保上传目录存在
        os.makedirs(upload_folder, exist_ok=True)

        self.logger.info(f"Web应用配置完成 - Debug: {self.app.config['DEBUG']}")

    def _register_routes(self):
        """注册基础路由"""

        @self.app.route('/')
        def index():
            """首页路由"""
            try:
                return render_template('index.html')
            except Exception as e:
                self.logger.error(f"渲染首页失败: {e}")
                return "<h1>AIDefectDetector</h1><p>Web界面正在开发中...</p>", 200

        @self.app.route('/health')
        def health_check():
            """健康检查路由"""
            return jsonify({
                'status': 'healthy',
                'service': 'AIDefectDetector',
                'version': '1.0.0'
            })

        @self.app.route('/api/info')
        def api_info():
            """API信息路由"""
            return jsonify({
                'name': 'AIDefectDetector',
                'description': '基于AI Agent的软件项目缺陷自主检测与修复系统',
                'version': '1.0.0',
                'modes': ['static', 'deep', 'fix']
            })

        @self.app.route('/api/upload', methods=['POST'])
        def upload_project():
            """项目文件上传API"""
            try:
                if 'file' not in request.files:
                    return jsonify({'error': '没有选择文件'}), 400

                file = request.files['file']
                if file.filename == '':
                    return jsonify({'error': '没有选择文件'}), 400

                # 验证文件类型
                allowed_extensions = {'.zip', '.tar', '.gz'}
                file_ext = os.path.splitext(file.filename)[1].lower()
                if file_ext not in allowed_extensions:
                    return jsonify({'error': '不支持的文件类型'}), 400

                # 验证文件大小
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)

                max_size = self.app.config.get('MAX_CONTENT_LENGTH', 50 * 1024 * 1024)
                if file_size > max_size:
                    return jsonify({'error': '文件太大'}), 400

                # 保存文件
                import uuid
                upload_folder = self.app.config['UPLOAD_FOLDER']
                file_id = str(uuid.uuid4())
                filename = f"{file_id}_{file.filename}"
                filepath = os.path.join(upload_folder, filename)

                file.save(filepath)

                self.logger.info(f"文件上传成功: {file.filename} -> {filepath}")

                return jsonify({
                    'success': True,
                    'file_id': file_id,
                    'filename': file.filename,
                    'size': file_size,
                    'path': filepath
                })

            except Exception as e:
                self.logger.error(f"文件上传失败: {e}")
                return jsonify({'error': f'上传失败: {str(e)}'}), 500

        @self.app.route('/api/validate-path', methods=['POST'])
        def validate_path():
            """路径验证API"""
            try:
                data = request.get_json()
                path = data.get('path', '').strip()

                if not path:
                    return jsonify({'valid': False, 'error': '路径不能为空'})

                # 安全检查：防止路径遍历攻击
                if '..' in path or path.startswith('/'):
                    return jsonify({'valid': False, 'error': '无效的路径格式'})

                # 检查路径是否存在
                import os
                if not os.path.exists(path):
                    return jsonify({'valid': False, 'error': '路径不存在'})

                if not os.path.isdir(path):
                    return jsonify({'valid': False, 'error': '路径不是目录'})

                # 检查是否包含代码文件
                code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.hpp'}
                has_code_files = False
                file_count = 0

                for root, dirs, files in os.walk(path):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in code_extensions):
                            has_code_files = True
                            file_count += 1
                        if file_count > 100:  # 限制扫描文件数量
                            break

                if not has_code_files:
                    return jsonify({'valid': False, 'error': '目录中未发现代码文件'})

                return jsonify({
                    'valid': True,
                    'message': f'发现 {file_count} 个代码文件',
                    'file_count': file_count
                })

            except Exception as e:
                self.logger.error(f"路径验证失败: {e}")
                return jsonify({'valid': False, 'error': '验证失败'})

        @self.app.route('/results')
        def results():
            """分析结果页面路由"""
            try:
                return render_template('results.html')
            except Exception as e:
                self.logger.error(f"渲染结果页面失败: {e}")
                return "<h1>AIDefectDetector</h1><p>结果页面正在开发中...</p>", 200

        @self.app.route('/api/analysis/start', methods=['POST'])
        def start_analysis():
            """启动分析任务API"""
            try:
                data = request.get_json()
                project_path = data.get('project_path')
                analysis_mode = data.get('mode', 'static')
                include_tests = data.get('include_tests', True)

                if not project_path:
                    return jsonify({'error': '项目路径不能为空'}), 400

                # 生成分析任务ID
                import uuid
                task_id = str(uuid.uuid4())

                # 这里应该启动后台分析任务
                # 目前返回模拟的任务ID
                self.logger.info(f"启动分析任务: {task_id} - {project_path} ({analysis_mode})")

                return jsonify({
                    'success': True,
                    'task_id': task_id,
                    'status': 'started',
                    'message': '分析任务已启动'
                })

            except Exception as e:
                self.logger.error(f"启动分析失败: {e}")
                return jsonify({'error': f'启动分析失败: {str(e)}'}), 500

        @self.app.route('/api/analysis/status/<task_id>')
        def get_analysis_status(task_id):
            """获取分析任务状态API"""
            try:
                # 这里应该查询实际的任务状态
                # 目前返回模拟状态
                import random

                # 模拟不同的任务状态
                statuses = ['running', 'completed', 'failed']
                weights = [0.3, 0.6, 0.1]  # 30%运行中，60%完成，10%失败

                status = random.choices(statuses, weights=weights)[0]

                response_data = {
                    'task_id': task_id,
                    'status': status,
                    'progress': random.randint(0, 100) if status == 'running' else 100
                }

                if status == 'completed':
                    response_data.update({
                        'total_issues': random.randint(5, 50),
                        'critical_issues': random.randint(0, 5),
                        'warning_issues': random.randint(2, 15),
                        'info_issues': random.randint(3, 30),
                        'completed_at': '2024-01-15 10:30:00'
                    })
                elif status == 'failed':
                    response_data.update({
                        'error': '分析过程中发生错误',
                        'failed_at': '2024-01-15 10:25:00'
                    })

                return jsonify(response_data)

            except Exception as e:
                self.logger.error(f"获取分析状态失败: {e}")
                return jsonify({'error': '获取状态失败'}), 500

        @self.app.route('/api/analysis/results/<task_id>')
        def get_analysis_results(task_id):
            """获取分析结果API"""
            try:
                # 这里应该从数据库或文件中读取实际的分析结果
                # 目前返回模拟数据
                mock_results = self._generate_mock_analysis_results(task_id)

                return jsonify({
                    'success': True,
                    'task_id': task_id,
                    'analysis_info': {
                        'project_name': '示例项目',
                        'project_path': '/path/to/project',
                        'analysis_mode': 'static',
                        'analysis_time': '2024-01-15 10:30:00',
                        'total_files_analyzed': 25,
                        'total_issues': len(mock_results),
                        'critical_count': len([i for i in mock_results if i['severity'] == 'critical']),
                        'warning_count': len([i for i in mock_results if i['severity'] == 'warning']),
                        'info_count': len([i for i in mock_results if i['severity'] == 'info'])
                    },
                    'issues': mock_results
                })

            except Exception as e:
                self.logger.error(f"获取分析结果失败: {e}")
                return jsonify({'error': '获取结果失败'}), 500

        @self.app.route('/api/analysis/export/<task_id>')
        def export_analysis_results(task_id):
            """导出分析结果API"""
            try:
                # 获取导出格式
                export_format = request.args.get('format', 'json').lower()

                if export_format not in ['json', 'csv', 'html']:
                    return jsonify({'error': '不支持的导出格式'}), 400

                # 这里应该获取实际的分析结果
                mock_results = self._generate_mock_analysis_results(task_id)

                if export_format == 'json':
                    return jsonify({
                        'success': True,
                        'format': 'json',
                        'data': mock_results,
                        'filename': f'analysis_results_{task_id}.json'
                    })

                elif export_format == 'csv':
                    # 生成CSV格式的数据
                    import csv
                    import io

                    output = io.StringIO()
                    writer = csv.writer(output)

                    # 写入表头
                    writer.writerow(['ID', '严重程度', '类别', '标题', '描述', '文件', '行号', '代码', '建议'])

                    # 写入数据
                    for issue in mock_results:
                        writer.writerow([
                            issue['id'],
                            issue['severity'],
                            issue['category'],
                            issue['title'],
                            issue['description'],
                            issue['file'],
                            issue['line'],
                            issue['code'],
                            issue['suggestion']
                        ])

                    csv_data = output.getvalue()
                    output.close()

                    return jsonify({
                        'success': True,
                        'format': 'csv',
                        'data': csv_data,
                        'filename': f'analysis_results_{task_id}.csv'
                    })

                elif export_format == 'html':
                    # 生成HTML格式的报告
                    html_content = self._generate_html_report(mock_results, task_id)

                    return jsonify({
                        'success': True,
                        'format': 'html',
                        'data': html_content,
                        'filename': f'analysis_results_{task_id}.html'
                    })

            except Exception as e:
                self.logger.error(f"导出分析结果失败: {e}")
                return jsonify({'error': '导出失败'}), 500

        self.logger.info("基础路由注册完成")

    def _register_error_handlers(self):
        """注册错误处理器"""

        @self.app.errorhandler(404)
        def not_found(error):
            """404错误处理"""
            if request.path.startswith('/api/'):
                return jsonify({'error': 'API endpoint not found'}), 404
            return render_template('404.html'), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            """500错误处理"""
            self.logger.error(f"内部服务器错误: {error}")
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Internal server error'}), 500
            return render_template('500.html'), 500

        @self.app.errorhandler(Exception)
        def handle_exception(error):
            """全局异常处理"""
            self.logger.error(f"未处理的异常: {error}", exc_info=True)
            if request.path.startswith('/api/'):
                return jsonify({'error': 'An unexpected error occurred'}), 500
            return render_template('500.html'), 500

        self.logger.info("错误处理器注册完成")

    def _generate_mock_analysis_results(self, task_id):
        """生成模拟分析结果数据"""
        import random

        # 定义问题类别和严重程度
        categories = ['syntax', 'style', 'security', 'performance', 'maintainability']
        severities = ['critical', 'warning', 'info']

        # 定义示例问题模板
        issue_templates = [
            {
                'category': 'security',
                'severity': 'critical',
                'title_pattern': '硬编码{type}风险',
                'description_pattern': '检测到可能的硬编码{type}，存在安全风险',
                'code_pattern': '{type} = "{value}"  # 硬编码{type}',
                'suggestion_pattern': '使用环境变量或配置文件存储敏感信息'
            },
            {
                'category': 'style',
                'severity': 'warning',
                'title_pattern': '行长度超过限制',
                'description_pattern': '代码行长度超过PEP8建议的79个字符',
                'code_pattern': 'long_variable_name_that_exceeds_pep8_line_length_limit = "{value}"',
                'suggestion_pattern': '将长行拆分为多行或使用更短的变量名'
            },
            {
                'category': 'performance',
                'severity': 'info',
                'title_pattern': '循环中的字符串拼接',
                'description_pattern': '在循环中使用+=操作符拼接字符串可能影响性能',
                'code_pattern': 'result += item',
                'suggestion_pattern': '使用列表收集元素，最后使用join()方法拼接'
            },
            {
                'category': 'syntax',
                'severity': 'critical',
                'title_pattern': '语法错误：{error_type}',
                'description_pattern': '代码中存在语法错误，无法正常解析',
                'code_pattern': 'def func({invalid_syntax})',
                'suggestion_pattern': '修复语法错误，确保代码符合Python语法规范'
            },
            {
                'category': 'maintainability',
                'severity': 'warning',
                'title_pattern': '函数复杂度过高',
                'description_pattern': '函数的圈复杂度过高，建议拆分为更小的函数',
                'code_pattern': 'def complex_function():\n    # 复杂逻辑...',
                'suggestion_pattern': '将复杂函数拆分为多个简单函数，提高代码可维护性'
            }
        ]

        # 定义文件名模板
        file_templates = [
            'src/auth/user_manager.py',
            'src/utils/helpers.py',
            'src/processors/data_processor.py',
            'src/models/database.py',
            'src/api/endpoints.py',
            'src/services/analysis_service.py',
            'src/config/settings.py',
            'src/cli/main.py',
            'src/tests/test_models.py',
            'src/web/routes.py'
        ]

        mock_results = []

        # 生成随机数量的问题（15-40个）
        issue_count = random.randint(15, 40)

        for i in range(1, issue_count + 1):
            # 随机选择问题模板
            template = random.choice(issue_templates)

            # 随机选择文件
            file_path = random.choice(file_templates)

            # 生成随机行号
            line_number = random.randint(1, 300)

            # 填充模板
            if template['category'] == 'security':
                types = ['密码', 'API密钥', '令牌']
                type_name = random.choice(types)
                values = ['admin123', 'secret_key', 'token123']
                value = random.choice(values)

                title = template['title_pattern'].format(type=type_name)
                description = template['description_pattern'].format(type=type_name)
                code = template['code_pattern'].format(type=type_name.lower(), value=value)
                suggestion = template['suggestion_pattern']

            elif template['category'] == 'syntax':
                error_types = '无效缩进', '缺少冒号', '括号不匹配'
                error_type = random.choice(error_types)
                invalid_syntaxes = 'param1, param2,', 'param1 param2', 'param1, param2'
                invalid_syntax = random.choice(invalid_syntaxes)

                title = template['title_pattern'].format(error_type=error_type)
                description = template['description_pattern']
                code = template['code_pattern'].format(invalid_syntax=invalid_syntax)
                suggestion = template['suggestion_pattern']

            else:
                title = template['title_pattern']
                description = template['description_pattern']
                code = template['code_pattern']
                suggestion = template['suggestion_pattern']

            issue = {
                'id': i,
                'severity': template['severity'],
                'category': template['category'],
                'title': title,
                'description': description,
                'file': file_path,
                'line': line_number,
                'code': code,
                'suggestion': suggestion,
                'rule_id': f'{template["category"].upper()}_{i:03d}',
                'confidence': random.randint(70, 100)
            }

            mock_results.append(issue)

        # 按严重程度和文件名排序
        severity_order = {'critical': 3, 'warning': 2, 'info': 1}
        mock_results.sort(key=lambda x: (-severity_order[x['severity']], x['file'], x['line']))

        return mock_results

    def _generate_html_report(self, results, task_id):
        """生成HTML格式的分析报告"""
        # 统计数据
        critical_count = len([r for r in results if r['severity'] == 'critical'])
        warning_count = len([r for r in results if r['severity'] == 'warning'])
        info_count = len([r for r in results if r['severity'] == 'info'])

        # 按文件分组
        file_groups = {}
        for result in results:
            if result['file'] not in file_groups:
                file_groups[result['file']] = []
            file_groups[result['file']].append(result)

        # 生成HTML
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>代码分析结果报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 40px; padding-bottom: 20px; border-bottom: 2px solid #dee2e6; }}
        .summary {{ display: flex; justify-content: space-around; margin: 30px 0; }}
        .summary-item {{ text-align: center; padding: 20px; border-radius: 8px; }}
        .critical {{ background-color: #f8d7da; color: #721c24; }}
        .warning {{ background-color: #fff3cd; color: #856404; }}
        .info {{ background-color: #d1ecf1; color: #0c5460; }}
        .file-section {{ margin: 30px 0; }}
        .file-header {{ background-color: #e9ecef; padding: 15px; border-radius: 5px 5px 0 0; font-weight: bold; }}
        .issues {{ border: 1px solid #dee2e6; border-top: none; }}
        .issue {{ padding: 15px; border-bottom: 1px solid #dee2e6; }}
        .issue:last-child {{ border-bottom: none; }}
        .issue-header {{ display: flex; justify-content: between; align-items: center; margin-bottom: 10px; }}
        .severity-badge {{ padding: 4px 8px; border-radius: 4px; color: white; font-size: 12px; }}
        .severity-critical {{ background-color: #dc3545; }}
        .severity-warning {{ background-color: #ffc107; color: #000; }}
        .severity-info {{ background-color: #17a2b8; }}
        .code {{ background-color: #f8f9fa; padding: 10px; border-radius: 4px; font-family: monospace; white-space: pre-wrap; margin: 10px 0; }}
        .suggestion {{ background-color: #d4edda; padding: 10px; border-radius: 4px; margin: 10px 0; }}
        .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AIDefectDetector 代码分析报告</h1>
            <p>任务ID: {task_id}</p>
            <p>生成时间: {self._get_current_time()}</p>
        </div>

        <div class="summary">
            <div class="summary-item critical">
                <h3>{critical_count}</h3>
                <p>严重问题</p>
            </div>
            <div class="summary-item warning">
                <h3>{warning_count}</h3>
                <p>警告问题</p>
            </div>
            <div class="summary-item info">
                <h3>{info_count}</h3>
                <p>信息问题</p>
            </div>
            <div class="summary-item">
                <h3>{len(results)}</h3>
                <p>总问题数</p>
            </div>
        </div>

        <h2>问题详情</h2>"""

        # 按文件生成问题列表
        for file_path, issues in file_groups.items():
            html += f"""
        <div class="file-section">
            <div class="file-header">
                <i class="fas fa-file-code"></i> {file_path} ({len(issues)} 个问题)
            </div>
            <div class="issues">"""

            for issue in issues:
                severity_class = f"severity-{issue['severity']}"
                severity_text = {'critical': '严重', 'warning': '警告', 'info': '信息'}[issue['severity']]

                html += f"""
                <div class="issue">
                    <div class="issue-header">
                        <span class="severity-badge {severity_class}">{severity_text}</span>
                        <strong>{issue['title']}</strong>
                        <span style="margin-left: auto; color: #6c757d;">行 {issue['line']}</span>
                    </div>
                    <p>{issue['description']}</p>
                    <div class="code">{issue['code']}</div>
                    <div class="suggestion">
                        <strong>修复建议:</strong> {issue['suggestion']}
                    </div>
                </div>"""

            html += """
            </div>
        </div>"""

        html += f"""
        <div class="footer">
            <p>报告由 AIDefectDetector 自动生成</p>
            <p>项目地址: https://github.com/your-repo/ai-defect-detector</p>
        </div>
    </div>
</body>
</html>"""

        return html

    def _get_current_time(self):
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def run(self, host=None, port=None, debug=None):
        """运行Web应用"""
        # 获取运行配置
        web_config = self.config.get('web', {})
        run_host = host or web_config.get('host', '127.0.0.1')
        run_port = port or web_config.get('port', 5000)
        run_debug = debug if debug is not None else web_config.get('debug', False)

        self.logger.info(f"启动Web应用 - http://{run_host}:{run_port}")

        try:
            self.app.run(
                host=run_host,
                port=run_port,
                debug=run_debug,
                threaded=True
            )
        except Exception as e:
            self.logger.error(f"启动Web应用失败: {e}")
            raise


def create_app():
    """创建Flask应用的工厂函数"""
    web_app = AIDefectDetectorWeb()
    return web_app.app


def main():
    """Web应用主入口函数"""
    try:
        print("AIDefectDetector Web界面")
        print("=" * 50)

        # 创建Web应用实例
        web_app = AIDefectDetectorWeb()

        # 获取配置
        web_config = web_app.config.get('web', {})
        host = web_config.get('host', '127.0.0.1')
        port = web_config.get('port', 5000)

        print(f"Web界面启动中...")
        print(f"访问地址: http://{host}:{port}")
        print("按 Ctrl+C 停止服务")
        print("=" * 50)

        # 运行应用
        web_app.run()

    except ImportError as e:
        print(f"错误: {e}")
        print("请安装Flask: pip install flask")
        return 1
    except Exception as e:
        print(f"启动Web应用失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
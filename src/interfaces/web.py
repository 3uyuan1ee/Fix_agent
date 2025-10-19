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
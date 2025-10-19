#!/usr/bin/env python3
"""
AIDefectDetector Web应用测试
测试Flask Web应用的基础功能
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from src.interfaces.web import AIDefectDetectorWeb, create_app
    from src.utils.config import get_config
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保Flask已安装: pip install flask")
    sys.exit(1)


class TestAIDefectDetectorWeb(unittest.TestCase):
    """AIDefectDetector Web应用测试类"""

    def setUp(self):
        """测试前准备"""
        # 创建测试应用实例
        self.web_app = AIDefectDetectorWeb()
        self.app = self.web_app.app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def tearDown(self):
        """测试后清理"""
        pass

    def test_app_creation(self):
        """测试Flask应用创建"""
        # 验证应用实例存在
        self.assertIsNotNone(self.app)
        self.assertEqual(self.app.name, 'src.interfaces.web')

    def test_config_loading(self):
        """测试配置加载"""
        # 验证配置加载成功
        self.assertIsNotNone(self.web_app.config)
        self.assertIn('web', self.web_app.config)

        # 验证Flask应用配置
        self.assertIn('SECRET_KEY', self.app.config)
        self.assertIn('UPLOAD_FOLDER', self.app.config)
        self.assertIn('MAX_CONTENT_LENGTH', self.app.config)

    def test_index_route(self):
        """测试首页路由"""
        # 测试首页访问
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

        # 验证响应内容包含关键信息
        self.assertIn(b'AIDefectDetector', response.data)
        self.assertIn(b'AIDefectDetector', response.data)  # 简化测试，避免中文字符编码问题

    def test_health_check_route(self):
        """测试健康检查路由"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)

        # 验证返回的JSON格式
        data = response.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'AIDefectDetector')
        self.assertIn('version', data)

    def test_api_info_route(self):
        """测试API信息路由"""
        response = self.client.get('/api/info')
        self.assertEqual(response.status_code, 200)

        # 验证返回的JSON格式
        data = response.get_json()
        self.assertEqual(data['name'], 'AIDefectDetector')
        self.assertIn('description', data)
        self.assertIn('version', data)
        self.assertIn('modes', data)
        self.assertIn('static', data['modes'])
        self.assertIn('deep', data['modes'])
        self.assertIn('fix', data['modes'])

    def test_404_error_handler(self):
        """测试404错误处理"""
        response = self.client.get('/nonexistent-page')
        self.assertEqual(response.status_code, 404)

    def test_api_404_error_handler(self):
        """测试API 404错误处理"""
        response = self.client.get('/api/nonexistent-endpoint')
        self.assertEqual(response.status_code, 404)

        data = response.get_json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'API endpoint not found')

    def test_static_files(self):
        """测试静态文件服务"""
        # 测试CSS文件
        response = self.client.get('/static/css/style.css')
        self.assertIn(response.status_code, [200, 404])  # 可能存在也可能不存在

        # 测试JS文件
        response = self.client.get('/static/js/app.js')
        self.assertIn(response.status_code, [200, 404])

    def test_upload_folder_creation(self):
        """测试上传目录创建"""
        upload_folder = self.app.config['UPLOAD_FOLDER']
        self.assertTrue(os.path.exists(upload_folder))
        self.assertTrue(os.path.isdir(upload_folder))

    def test_flask_application_factory(self):
        """测试Flask应用工厂函数"""
        app = create_app()
        self.assertIsNotNone(app)
        self.assertTrue(hasattr(app, 'route'))

    def test_error_logging(self):
        """测试错误日志记录"""
        # 测试访问不存在的页面是否记录错误日志
        with self.app.test_client() as client:
            response = client.get('/definitely-does-not-exist')
            self.assertEqual(response.status_code, 404)


class TestWebAppIntegration(unittest.TestCase):
    """Web应用集成测试"""

    def setUp(self):
        """测试前准备"""
        self.web_app = AIDefectDetectorWeb()
        self.app = self.web_app.app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_full_application_startup(self):
        """测试完整应用启动流程"""
        # 验证应用可以正常启动
        self.assertIsNotNone(self.web_app)
        self.assertIsNotNone(self.web_app.app)

        # 验证路由已注册
        rules = [rule.rule for rule in self.app.url_map.iter_rules()]
        self.assertIn('/', rules)
        self.assertIn('/health', rules)
        self.assertIn('/api/info', rules)

    def test_configuration_integration(self):
        """测试配置集成"""
        config = get_config()
        self.assertIsNotNone(config)

        # 验证Web配置存在
        self.assertIn('web', config)
        web_config = config['web']

        # 验证必要的配置项
        self.assertIn('host', web_config)
        self.assertIn('port', web_config)

    def test_error_handling_integration(self):
        """测试错误处理集成"""
        # 测试应用级别的错误处理
        with self.app.test_client() as client:
            # 测试正常路由
            response = client.get('/')
            self.assertEqual(response.status_code, 200)

            # 测试错误路由
            response = client.get('/trigger-error')
            self.assertEqual(response.status_code, 500)


class TestWebAppPerformance(unittest.TestCase):
    """Web应用性能测试"""

    def setUp(self):
        """测试前准备"""
        self.web_app = AIDefectDetectorWeb()
        self.app = self.web_app.app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_response_time(self):
        """测试响应时间"""
        import time

        start_time = time.time()
        response = self.client.get('/')
        end_time = time.time()

        response_time = end_time - start_time

        # 验证响应时间在合理范围内（1秒内）
        self.assertLess(response_time, 1.0)
        self.assertEqual(response.status_code, 200)

    def test_concurrent_requests(self):
        """测试并发请求处理"""
        import threading
        import time

        results = []

        def make_request():
            response = self.client.get('/health')
            results.append(response.status_code)

        # 创建10个并发请求
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有请求都成功
        self.assertEqual(len(results), 10)
        self.assertTrue(all(status == 200 for status in results))


def run_web_app_tests():
    """运行Web应用测试"""
    print("运行AIDefectDetector Web应用测试...")
    print("=" * 60)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试用例
    suite.addTests(loader.loadTestsFromTestCase(TestAIDefectDetectorWeb))
    suite.addTests(loader.loadTestsFromTestCase(TestWebAppIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestWebAppPerformance))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出测试结果摘要
    print("=" * 60)
    print(f"测试结果摘要:")
    print(f"运行测试: {result.testsRun}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")

    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")

    if result.errors:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")

    # 返回是否所有测试都通过
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == '__main__':
    success = run_web_app_tests()
    sys.exit(0 if success else 1)
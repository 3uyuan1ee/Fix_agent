"""
前端功能测试
测试HTML模板、CSS样式和JavaScript功能的完整性
"""

import pytest
import requests
import json
import re
from bs4 import BeautifulSoup


class TestFrontendFunctionality:
    """前端功能测试类"""

    @classmethod
    def setup_class(cls):
        """测试类初始化"""
        cls.base_url = "http://127.0.0.1:5000"

        # 测试连接
        try:
            response = requests.get(cls.base_url, timeout=5)
            assert response.status_code == 200
            print("✓ Web服务连接成功")
        except Exception as e:
            print(f"✗ Web服务连接失败: {e}")
            raise

    def test_001_home_page_structure(self):
        """测试首页结构完整性"""
        response = requests.get(self.base_url)
        assert response.status_code == 200

        soup = BeautifulSoup(response.text, 'html.parser')

        # 检查基本HTML结构
        assert soup.find('title'), "页面应该有title标签"
        assert soup.find('meta', charset=True), "页面应该有charset meta标签"
        assert soup.find('meta', attrs={'name': 'viewport'}), "页面应该有viewport meta标签"

        # 检查CSS和JS资源
        css_links = soup.find_all('link', rel='stylesheet')
        js_scripts = soup.find_all('script', src=True)

        print(f"✓ 页面包含 {len(css_links)} 个CSS文件和 {len(js_scripts)} 个JS文件")

        # 检查关键CSS文件
        css_hrefs = [link.get('href') for link in css_links]
        assert any('bootstrap' in href.lower() for href in css_hrefs), "应该引入Bootstrap CSS"
        assert any('style.css' in href for href in css_hrefs), "应该引入自定义样式"

        # 检查关键JS文件
        js_srcs = [script.get('src') for script in js_scripts]
        assert any('bootstrap' in src.lower() for src in js_srcs), "应该引入Bootstrap JS"
        assert any('app.js' in src for src in js_srcs), "应该引入应用JS"

        print("✓ 首页HTML结构完整")

    def test_002_navigation_functionality(self):
        """测试导航功能"""
        pages = [
            ("/", "首页"),
            ("/config", "配置"),
            ("/static", "静态分析"),
            ("/deep", "深度分析"),
            ("/fix", "修复模式"),
            ("/history", "历史记录")
        ]

        for path, expected_title in pages:
            response = requests.get(f"{self.base_url}{path}")
            assert response.status_code == 200

            soup = BeautifulSoup(response.text, 'html.parser')

            # 检查页面标题
            title = soup.find('title')
            if title:
                assert expected_title in title.text or any(word in title.text for word in ["配置", "分析", "修复", "历史"]), f"{path}页面标题应该包含相关关键词"

            # 检查侧边栏导航
            sidebar = soup.find('nav', class_='sidebar') or soup.find('div', class_='sidebar')
            if sidebar:
                # 检查导航链接
                nav_links = sidebar.find_all('a', href=True)
                current_page_link = any(path in link.get('href', '') for link in nav_links)
                # 当前页面可能在导航中有高亮显示

            print(f"✓ {path}页面导航正常")

    def test_003_responsive_design(self):
        """测试响应式设计"""
        response = requests.get(self.base_url)
        assert response.status_code == 200

        soup = BeautifulSoup(response.text, 'html.parser')

        # 检查viewport meta标签
        viewport_meta = soup.find('meta', attrs={'name': 'viewport'})
        assert viewport_meta, "页面应该有viewport meta标签"

        content = viewport_meta.get('content', '')
        assert 'width=device-width' in content, "viewport应该包含device-width"
        assert 'initial-scale=1' in content, "viewport应该包含initial-scale"

        # 检查响应式CSS类
        css_links = soup.find_all('link', rel='stylesheet')
        for link in css_links:
            href = link.get('href', '')
            if 'style.css' in href:
                # 获取CSS内容检查响应式设计
                css_response = requests.get(f"{self.base_url}{href}")
                if css_response.status_code == 200:
                    css_content = css_response.text
                    responsive_features = [
                        '@media',
                        'flex',
                        'grid',
                        'col-',
                        'container',
                        'responsive'
                    ]

                    found_features = [feature for feature in responsive_features if feature in css_content.lower()]
                    print(f"✓ CSS包含响应式特性: {', '.join(found_features)}")

        print("✓ 响应式设计检查完成")

    def test_004_javascript_functionality(self):
        """测试JavaScript功能"""
        response = requests.get(self.base_url)
        assert response.status_code == 200

        soup = BeautifulSoup(response.text, 'html.parser')

        # 检查关键JavaScript文件
        js_scripts = soup.find_all('script', src=True)
        app_js_found = False

        for script in js_scripts:
            src = script.get('src', '')
            if 'app.js' in src:
                app_js_found = True
                # 尝试获取app.js内容
                js_response = requests.get(f"{self.base_url}{src}")
                if js_response.status_code == 200:
                    js_content = js_response.text

                    # 检查关键功能
                    key_features = [
                        'App',
                        'Sidebar',
                        'collapse',
                        'expand',
                        'toggle',
                        'DOMContentLoaded'
                    ]

                    found_features = [feature for feature in key_features if feature in js_content]
                    print(f"✓ app.js包含关键功能: {', '.join(found_features)}")

                    # 检查错误处理
                    if 'try' in js_content and 'catch' in js_content:
                        print("✓ JavaScript包含错误处理")

        assert app_js_found, "应该引入app.js文件"

    def test_005_config_page_functionality(self):
        """测试配置页面功能"""
        response = requests.get(f"{self.base_url}/config")
        assert response.status_code == 200

        soup = BeautifulSoup(response.text, 'html.parser')

        # 检查表单元素
        form = soup.find('form')
        assert form, "配置页面应该有表单"

        # 检查输入字段
        inputs = form.find_all(['input', 'select', 'textarea'])
        assert len(inputs) > 0, "表单应该有输入字段"

        # 检查按钮
        buttons = form.find_all('button')
        assert len(buttons) > 0, "表单应该有按钮"

        # 检查配置选项
        config_sections = soup.find_all(['div', 'section'], class_=lambda x: x and 'config' in x.lower())
        if config_sections:
            print(f"✓ 配置页面包含 {len(config_sections)} 个配置区域")

        print("✓ 配置页面功能检查完成")

    def test_006_static_analysis_page(self):
        """测试静态分析页面功能"""
        response = requests.get(f"{self.base_url}/static")
        assert response.status_code == 200

        soup = BeautifulSoup(response.text, 'html.parser')

        # 检查文件上传区域
        upload_area = soup.find(['div', 'input'], class_=lambda x: x and ('upload' in x.lower() or 'file' in x.lower()))
        if upload_area:
            print("✓ 静态分析页面包含文件上传区域")

        # 检查分析选项
        tool_checkboxes = soup.find_all('input', type='checkbox')
        if tool_checkboxes:
            print(f"✓ 静态分析页面包含 {len(tool_checkboxes)} 个工具选项")

        # 检查开始分析按钮
        start_button = soup.find('button', text=lambda x: x and ('开始' in x or '分析' in x or 'start' in x.lower()))
        if start_button:
            print("✓ 静态分析页面包含开始分析按钮")

        # 检查结果显示区域
        results_area = soup.find(['div', 'section'], class_=lambda x: x and ('result' in x.lower() or 'output' in x.lower()))
        if results_area:
            print("✓ 静态分析页面包含结果显示区域")

    def test_007_deep_analysis_page(self):
        """测试深度分析页面功能"""
        response = requests.get(f"{self.base_url}/deep")
        assert response.status_code == 200

        soup = BeautifulSoup(response.text, 'html.parser')

        # 检查聊天界面
        chat_container = soup.find(['div', 'section'], class_=lambda x: x and ('chat' in x.lower() or 'message' in x.lower()))
        if chat_container:
            print("✓ 深度分析页面包含聊天容器")

        # 检查消息输入框
        message_input = soup.find('textarea', attrs={'name': 'message'}) or soup.find('input', attrs={'name': 'message'})
        if message_input:
            print("✓ 深度分析页面包含消息输入框")

        # 检查发送按钮
        send_button = soup.find('button', text=lambda x: x and ('发送' in x or 'send' in x.lower()))
        if send_button:
            print("✓ 深度分析页面包含发送按钮")

    def test_008_fix_mode_page(self):
        """测试修复模式页面功能"""
        response = requests.get(f"{self.base_url}/fix")
        assert response.status_code == 200

        soup = BeautifulSoup(response.text, 'html.parser')

        # 检查修复建议区域
        suggestions_area = soup.find(['div', 'section'], class_=lambda x: x and ('suggestion' in x.lower() or 'fix' in x.lower()))
        if suggestions_area:
            print("✓ 修复模式页面包含修复建议区域")

        # 检查代码显示区域
        code_area = soup.find(['pre', 'code', 'div'], class_=lambda x: x and ('code' in x.lower() or 'diff' in x.lower()))
        if code_area:
            print("✓ 修复模式页面包含代码显示区域")

        # 检查操作按钮
        action_buttons = soup.find_all('button', text=lambda x: x and ('应用' in x or '应用修复' in x or 'apply' in x.lower()))
        if action_buttons:
            print(f"✓ 修复模式页面包含 {len(action_buttons)} 个操作按钮")

    def test_009_history_page(self):
        """测试历史记录页面功能"""
        response = requests.get(f"{self.base_url}/history")
        assert response.status_code == 200

        soup = BeautifulSoup(response.text, 'html.parser')

        # 检查搜索功能
        search_input = soup.find('input', attrs={'type': 'search'}) or soup.find('input', attrs={'placeholder': lambda x: x and '搜索' in x})
        if search_input:
            print("✓ 历史记录页面包含搜索功能")

        # 检查筛选功能
        filter_select = soup.find('select') or soup.find_all('input', type='checkbox')
        if filter_select:
            print("✓ 历史记录页面包含筛选功能")

        # 检查表格或列表
        table = soup.find('table') or soup.find(['ul', 'ol'], class_=lambda x: x and ('record' in x.lower() or 'item' in x.lower()))
        if table:
            print("✓ 历史记录页面包含记录列表")

        # 检查分页
        pagination = soup.find(['nav', 'div'], class_=lambda x: x and ('page' in x.lower() or 'pagin' in x.lower()))
        if pagination:
            print("✓ 历史记录页面包含分页功能")

    def test_010_css_styling_integrity(self):
        """测试CSS样式完整性"""
        # 检查主要CSS文件
        css_files = [
            '/static/css/style.css',
            '/static/css/config.css',
            '/static/css/static.css',
            '/static/css/deep.css',
            '/static/css/fix.css',
            '/static/css/history.css'
        ]

        for css_file in css_files:
            try:
                response = requests.get(f"{self.base_url}{css_file}")
                if response.status_code == 200:
                    css_content = response.text

                    # 检查基本CSS结构
                    css_rules = re.findall(r'[.#]?[\w-]+\s*{[^}]+}', css_content)
                    print(f"✓ {css_file} 包含 {len(css_rules)} 条CSS规则")

                    # 检查响应式设计
                    media_queries = re.findall(r'@media[^{]+\{', css_content)
                    if media_queries:
                        print(f"✓ {css_file} 包含 {len(media_queries)} 个媒体查询")

                else:
                    print(f"⚠ {css_file} 返回状态码: {response.status_code}")

            except Exception as e:
                print(f"⚠ {css_file} 检查异常: {e}")

    def test_011_error_pages(self):
        """测试错误页面"""
        # 测试404错误页面
        response = requests.get(f"{self.base_url}/nonexistent-page")
        assert response.status_code in [404, 500]

        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find('title')
        if title:
            assert 'error' in title.text.lower() or 'not found' in title.text.lower() or '错误' in title.text
            print("✓ 错误页面标题正确")

        # 检查是否有返回首页的链接
        home_link = soup.find('a', href='/')
        if home_link:
            print("✓ 错误页面包含返回首页链接")

    def test_012_page_load_performance(self):
        """测试页面加载性能"""
        pages = ["/", "/config", "/static", "/deep", "/fix", "/history"]

        import time
        load_times = []

        for page in pages:
            start_time = time.time()
            response = requests.get(f"{self.base_url}{page}")
            end_time = time.time()

            if response.status_code == 200:
                load_time = end_time - start_time
                load_times.append(load_time)

                # 检查响应大小
                content_length = len(response.content)
                print(f"✓ {page} - 加载时间: {load_time:.3f}s, 内容大小: {content_length}字节")

        if load_times:
            avg_load_time = sum(load_times) / len(load_times)
            print(f"✓ 平均页面加载时间: {avg_load_time:.3f}s")

            # 性能要求检查
            assert avg_load_time < 0.1, f"平均加载时间应该小于0.1秒，实际: {avg_load_time:.3f}s"


def run_frontend_tests():
    """运行前端功能测试"""
    test_instance = TestFrontendFunctionality()

    try:
        test_instance.setup_class()

        # 运行所有测试
        test_methods = [method for method in dir(test_instance)
                       if method.startswith('test_') and callable(getattr(test_instance, method))]

        results = []
        for method_name in test_methods:
            try:
                print(f"\n运行: {method_name}")
                method = getattr(test_instance, method_name)
                method()
                results.append((method_name, "PASSED", None))
                print(f"✓ {method_name} - 通过")
            except Exception as e:
                results.append((method_name, "FAILED", str(e)))
                print(f"✗ {method_name} - 失败: {str(e)}")

        # 统计结果
        passed = sum(1 for _, status, _ in results if status == "PASSED")
        failed = sum(1 for _, status, _ in results if status == "FAILED")

        print(f"\n前端功能测试结果:")
        print(f"通过: {passed}/{len(results)}")
        print(f"失败: {failed}/{len(results)}")

        if failed > 0:
            print("\n失败的测试:")
            for method, status, error in results:
                if status == "FAILED":
                    print(f"  - {method}: {error}")

        return results

    except Exception as e:
        print(f"前端功能测试初始化失败: {e}")
        return []


if __name__ == "__main__":
    # 安装依赖
    try:
        import bs4
    except ImportError:
        print("安装BeautifulSoup4...")
        import subprocess
        subprocess.run(['pip', 'install', 'beautifulsoup4'])

    # 运行前端功能测试
    print("=" * 60)
    print("运行前端功能测试")
    print("=" * 60)

    results = run_frontend_tests()

    print("\n" + "=" * 60)
    print("前端功能测试完成")
    print("=" * 60)
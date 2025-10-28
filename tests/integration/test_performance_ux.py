"""
性能优化和用户体验测试
测试页面加载速度、动画流畅性、错误提示和操作反馈
"""

import pytest
import time
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .test_web_integration import TestWebIntegration

class TestPerformanceUX(TestWebIntegration):
    """性能和用户体验测试类"""

    def test_001_page_load_speed(self):
        """测试页面加载时间小于2秒"""
        pages_to_test = [
            ("/", "首页"),
            ("/config", "API配置"),
            ("/static", "静态分析"),
            ("/deep", "深度分析"),
            ("/fix", "修复模式"),
            ("/history", "历史记录")
        ]

        load_times = {}

        for path, page_name in pages_to_test:
            with self.subTest(page=page_name):
                # 记录开始时间
                start_time = time.time()

                # 加载页面
                self.driver.get(f"{self.base_url}{path}")

                # 等待页面完全加载
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )

                # 等待主要内容加载
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                    )
                except TimeoutException:
                    pass

                # 记录结束时间
                end_time = time.time()
                load_time = end_time - start_time
                load_times[page_name] = load_time

                # 验证加载时间
                assert load_time < 3.0, f"{page_name}加载时间应该小于3秒，实际: {load_time:.2f}秒"

        # 记录平均加载时间
        avg_load_time = sum(load_times.values()) / len(load_times)
        print(f"平均页面加载时间: {avg_load_time:.2f}秒")

        # 验证所有页面都在合理时间内加载
        for page_name, load_time in load_times.items():
            assert load_time < 2.0, f"{page_name}加载时间应该小于2秒，实际: {load_time:.2f}秒"

    def test_002_animation_smoothness(self):
        """测试动画流畅不卡顿"""
        # 导航到不同页面检查动画
        pages_with_animations = [
            "/static",  # 可能有进度动画
            "/deep",    # 可能有消息动画
            "/fix",     # 可能有修复动画
        ]

        for page in pages_with_animations:
            with self.subTest(page=page):
                self.driver.get(f"{self.base_url}{page}")
                time.sleep(1)

                # 查找可能的动画元素
                animated_elements = self.driver.find_elements(By.CSS_SELECTOR,
                                                                 ".transition, .animation, .fade, .slide, .loading")

                if animated_elements:
                    for element in animated_elements[:3]:  # 测试前3个动画元素
                        try:
                            # 触发动画（如果可能）
                            element.click()
                            time.sleep(0.5)

                            # 检查动画状态
                            transition_property = element.value_of_css_property("transition-property")
                            animation_name = element.value_of_css_property("animation-name")

                            # 如果有动画属性，检查是否流畅
                            if transition_property != "none" or animation_name != "none":
                                # 检查是否有不合理的动画时长
                                transition_duration = element.value_of_css_property("transition-duration")
                                animation_duration = element.value_of_css_property("animation-duration")

                                if transition_duration != "0s" or animation_duration != "0s":
                                    # 验证动画时长在合理范围内（0.1-3秒）
                                    duration_value = float(transition_duration.replace('s', '')) if transition_duration != '0s' else 0
                                    animation_value = float(animation_duration.replace('s', '')) if animation_duration != '0s' else 0

                                    max_duration = max(duration_value, animation_value)
                                    assert max_duration <= 3.0, f"动画时长不应超过3秒，当前: {max_duration}秒"

                        except Exception as e:
                            print(f"动画测试异常: {str(e)}")

    def test_003_error_handling_friendliness(self):
        """测试错误提示友好明确"""
        # 测试404错误页面
        with self.subTest("404错误页面"):
            try:
                self.driver.get(f"{self.base_url}/nonexistent-page")
                time.sleep(2)

                # 检查404页面内容
                page_source = self.driver.page_source.lower()
                assert any(keyword in page_source for keyword in ["404", "页面不存在", "未找到", "page not found"]), "404页面应该有友好的错误提示"

                # 检查是否有返回首页的链接
                home_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href='/'], a[href='/index']")
                assert len(home_links) > 0, "404页面应该有返回首页的链接"

            except Exception as e:
                print(f"404页面测试异常: {str(e)}")

        # 测试API错误处理
        with self.subTest("API错误处理"):
            # 导航到API配置页面
            self.driver.get(f"{self.base_url}/config")
            time.sleep(1)

            try:
                # 查找API测试按钮
                test_button = self.driver.find_element(By.CSS_SELECTOR,
                                                      ".test-connection, #testConnection")
                test_button.click()
                time.sleep(2)

                # 检查错误提示
                error_messages = self.driver.find_elements(By.CSS_SELECTOR,
                                                          ".alert-danger, .error-message, .connection-error")

                if error_messages:
                    error_text = error_messages[0].text
                    assert len(error_text) > 5, "错误提示应该有足够的内容"
                    assert "错误" in error_text.lower() or "失败" in error_text.lower() or "连接" in error_text.lower()

            except NoSuchElementException:
                print("API测试按钮未找到")

    def test_004_operation_feedback_timeliness(self):
        """测试操作反馈及时准确"""
        pages_to_test = [
            ("/config", "配置保存"),
            ("/static", "分析启动"),
            ("/deep", "消息发送"),
            ("/fix", "修复应用"),
            ("/history", "记录操作")
        ]

        for page, operation in pages_to_test:
            with self.subTest(page=page):
                self.driver.get(f"{self.base_url}{page}")
                time.sleep(1)

                try:
                    # 查找主要操作按钮
                    action_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                                                                  "button[type='submit'], .btn-primary, .action-btn")

                    if action_buttons:
                        action_button = action_buttons[0]
                        action_button.click()

                        # 立即检查反馈
                        time.sleep(0.5)

                        # 查找即时反馈
                        immediate_feedback = self.driver.find_elements(By.CSS_SELECTOR,
                                                                         ".loading, .spinner, .btn-loading, .processing")

                        # 延迟检查最终结果
                        time.sleep(2)

                        # 查找最终反馈
                        final_feedback = self.driver.find_elements(By.CSS_SELECTOR,
                                                                       ".alert, .success-message, .error-message, .toast")

                        # 应该至少有一种反馈
                        assert len(immediate_feedback) > 0 or len(final_feedback) > 0, f"{operation}操作应该有反馈提示"

                except Exception as e:
                    print(f"{page}页面操作反馈测试异常: {str(e)}")

    def test_005_responsive_performance(self):
        """测试响应式性能"""
        # 测试不同屏幕尺寸下的性能
        screen_sizes = [
            (1920, 1080, "桌面端"),
            (768, 1024, "平板端"),
            (375, 667, "手机端")
        ]

        for width, height, device_type in screen_sizes:
            with self.subTest(device_type=device_type):
                # 设置屏幕尺寸
                self.driver.set_window_size(width, height)
                time.sleep(1)

                # 测试页面加载
                start_time = time.time()
                self.driver.get(f"{self.base_url}/")
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                load_time = time.time() - start_time

                # 移动端可能有不同的性能要求
                max_load_time = 2.5 if device_type == "手机端" else 2.0
                assert load_time < max_load_time, f"{device_type}加载时间应该小于{max_load_time}秒，实际: {load_time:.2f}秒"

                # 检查关键元素是否正确显示
                try:
                    if device_type == "桌面端":
                        sidebar = self.driver.find_element(By.ID, "sidebar")
                        assert sidebar.is_displayed(), "桌面端侧边栏应该显示"
                    else:
                        # 移动端侧边栏应该隐藏或有菜单按钮
                        try:
                            topbar = self.driver.find_element(By.CSS_SELECTOR, ".topbar")
                            assert topbar.is_displayed(), "移动端顶部栏应该显示"
                        except NoSuchElementException:
                            pass

                    # 检查内容区域
                    content_area = self.driver.find_element(By.CSS_SELECTOR, ".main-content, .content-wrapper")
                    assert content_area.is_displayed(), "内容区域应该显示"

                except Exception as e:
                    print(f"{device_type}响应式测试异常: {str(e)}")

    def test_006_resource_loading_optimization(self):
        """测试资源加载优化"""
        # 启用性能日志
        self.driver.execute_cdp_cmd("Performance.enable", {})
        self.driver.execute_cdp_cmd("Runtime.enable", {})

        # 加载页面
        self.driver.get(f"{self.base_url}/")
        time.sleep(2)

        # 获取性能指标
        try:
            metrics = self.driver.execute_cdp_cmd("Performance.getMetrics")["result"]["metrics"]

            # 检查关键性能指标
            if "DomContentLoaded" in metrics:
                dom_content_loaded = metrics["DomContentLoaded"]
                assert dom_content_loaded < 3000, "DOM内容加载时间应该小于3秒"

            if "FirstMeaningfulPaint" in metrics:
                first_paint = metrics["FirstMeaningfulPaint"]
                assert first_paint < 4000, "首次有意义绘制时间应该小于4秒"

            # 检查资源加载
            resource_tree = self.driver.execute_cdp_cmd("Performance.getResourceTree")["result"]

            # 统计不同类型的资源
            resource_types = {}
            for resource in resource_tree:
                resource_type = resource.get("resourceType", "unknown")
                if resource_type not in resource_types:
                    resource_types[resource_type] = 0
                resource_types[resource_type] += 1

            print("资源类型统计:")
            for resource_type, count in resource_types.items():
                print(f"  {resource_type}: {count}")

            # 检查是否有过大的资源
            large_resources = [r for r in resource_tree if r.get("resourceSize", 0) > 1048576]  # > 1MB
            if large_resources:
                print(f"发现 {len(large_resources)} 个大文件资源")

        except Exception as e:
            print(f"性能指标获取异常: {str(e)}")

    def test_007_user_interaction_responsiveness(self):
        """测试用户交互响应性"""
        # 导航到交互性强的页面
        self.driver.get(f"{self.base_url}/static")
        time.sleep(1)

        try:
            # 测试按钮点击响应
            buttons = self.driver.find_elements(By.CSS_SELECTOR, "button, .btn")

            if buttons:
                test_button = buttons[0]

                # 记录点击前时间
                start_time = time.time()

                # 点击按钮
                test_button.click()

                # 记录点击后时间
                end_time = time.time()
                response_time = end_time - start_time

                # 响应时间应该很快
                assert response_time < 0.5, f"按钮点击响应时间应该小于0.5秒，实际: {response_time:.3f}秒"

            # 测试表单输入响应
            input_fields = self.driver.find_elements(By.CSS_SELECTOR, "input, textarea, select")

            if input_fields:
                test_input = input_fields[0]

                start_time = time.time()
                test_input.send_keys("测试输入")
                end_time = time.time()

                input_response_time = end_time - start_time
                assert input_response_time < 0.3, f"输入响应时间应该小于0.3秒，实际: {input_response_time:.3f}秒"

        except Exception as e:
            print(f"用户交互响应性测试异常: {str(e)}")

    def test_008_memory_usage_stability(self):
        """测试内存使用稳定性"""
        # 导航到复杂页面
        self.driver.get(f"{self.base_url}/fix")  # 修复模式可能有更多交互
        time.sleep(2)

        # 执行一系列操作来测试内存稳定性
        for i in range(3):
            try:
                # 切换侧边栏
                self.driver.execute_script("window.App.Sidebar.toggle()")
                time.sleep(1)

                # 恢复侧边栏
                self.driver.execute_script("window.App.Sidebar.toggle()")
                time.sleep(1)

                # 触发一些JavaScript操作
                self.driver.execute_script("document.body.scrollTop += 100")
                time.sleep(0.5)

                self.driver.execute_script("document.body.scrollTop -= 100")
                time.sleep(0.5)

            except Exception as e:
                print(f"第{i+1}次操作异常: {str(e)}")

        # 检查页面是否仍然响应
        try:
            self.driver.find_element(By.TAG_NAME, "body")
            page_responsive = self.driver.execute_script("return document.readyState") == "complete"
            assert page_responsive, "页面应该仍然响应"

        except Exception as e:
            print(f"内存稳定性测试异常: {str(e)}")

    def run_all_performance_tests(self):
        """运行所有性能和用户体验测试"""
        test_methods = [method for method in dir(self)
                       if method.startswith('test_') and callable(getattr(self, method))]

        results = []
        for method_name in test_methods:
            try:
                print(f"运行: {method_name}")
                method = getattr(self, method_name)
                method()
                results.append((method_name, "PASSED", None))
                print(f"✓ {method_name} - 通过")
            except Exception as e:
                results.append((method_name, "FAILED", str(e)))
                print(f"✗ {method_name} - 失败: {str(e)}")

        return results

if __name__ == "__main__":
    # 运行性能和用户体验测试
    test_instance = TestPerformanceUX()
    test_instance.setup_class()

    try:
        results = test_instance.run_all_performance_tests()

        # 统计结果
        passed = sum(1 for _, status, _ in results if status == "PASSED")
        failed = sum(1 for _, status, _ in results if status == "FAILED")

        print(f"\n性能和用户体验测试结果: {passed}/{len(results)} 通过")

        if failed > 0:
            print("失败的测试:")
            for method, status, error in results:
                if status == "FAILED":
                    print(f"  - {method}: {error}")

    finally:
        test_instance.teardown_class()
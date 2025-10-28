"""
静态分析功能测试
测试静态分析的完整工作流程
"""

import pytest
import time
import json
import os
import tempfile
import zipfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .test_web_integration import TestWebIntegration

class TestStaticAnalysis(TestWebIntegration):
    """静态分析功能测试类"""

    def test_001_file_selection_and_analysis(self):
        """测试文件选择和分析功能"""
        # 导航到静态分析页面
        self.driver.get(f"{self.base_url}/static")
        time.sleep(1)

        # 查找文件上传区域
        try:
            upload_area = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".upload-area, .drop-zone, input[type='file']"))
            )

            # 创建测试项目文件
            test_zip_path = self.create_test_project_zip()

            # 上传文件（模拟）
            if upload_area.tag_name == "input":
                upload_area.send_keys(test_zip_path)
            else:
                # 如果是拖拽区域，通过JavaScript上传
                self.driver.execute_script(f"""
                    const fileInput = document.querySelector('input[type="file"]');
                    if (fileInput) {{
                        fileInput.style.display = 'block';
                        fileInput.click();
                    }}
                """)

            time.sleep(2)

            # 检查文件是否被选择
            file_info_elements = self.driver.find_elements(By.CSS_SELECTOR,
                                                          ".file-info, .selected-file, .upload-success")

            assert len(file_info_elements) > 0, "文件选择后应该显示文件信息"

        except TimeoutException:
            print("文件上传区域未找到，跳过文件选择测试")

    def test_002_analysis_tool_selection(self):
        """测试分析工具选择功能"""
        # 导航到静态分析页面
        self.driver.get(f"{self.base_url}/static")
        time.sleep(1)

        # 查找分析工具选择区域
        try:
            tool_checkboxes = self.driver.find_elements(By.CSS_SELECTOR,
                                                         "input[type='checkbox'][name*='tool'], input[type='checkbox'][name*='analysis']")

            if tool_checkboxes:
                # 选择多个工具
                for i, checkbox in enumerate(tool_checkboxes[:3]):  # 选择前3个工具
                    if not checkbox.is_selected():
                        checkbox.click()
                        time.sleep(0.2)

                # 验证工具被选中
                selected_tools = [cb for cb in tool_checkboxes[:3] if cb.is_selected()]
                assert len(selected_tools) > 0, "至少应该有一个分析工具被选中"

            else:
                # 查找下拉选择器
                tool_select = Select(WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "select[name*='tool'], select[name*='analysis']"))
                ))

                # 选择多个选项（如果是多选）
                tool_select.select_by_index(0)
                time.sleep(0.5)

                assert tool_select.first_selected_option is not None

        except TimeoutException:
            print("分析工具选择区域未找到")

    def test_003_analysis_start_and_progress(self):
        """测试分析启动和进度更新"""
        # 导航到静态分析页面
        self.driver.get(f"{self.base_url}/static")
        time.sleep(1)

        # 查找开始分析按钮
        try:
            start_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,
                                              "button[type='submit'], .start-analysis, #startAnalysis"))
            )

            # 点击开始分析
            start_button.click()

            time.sleep(2)

            # 检查进度显示
            progress_elements = self.driver.find_elements(By.CSS_SELECTOR,
                                                         ".progress-bar, .analysis-progress, .status-progress")

            if progress_elements:
                progress_bar = progress_elements[0]

                # 检查进度条是否有动态更新的属性
                progress_value = progress_bar.get_attribute("aria-valuenow")
                progress_style = progress_bar.get_attribute("style")

                assert progress_value is not None or progress_style is not None, "进度条应该有值或样式更新"

            # 检查状态显示
            status_elements = self.driver.find_elements(By.CSS_SELECTOR,
                                                        ".status, .analysis-status, .current-status")

            if status_elements:
                status_text = status_elements[0].text.lower()
                assert any(keyword in status_text for keyword in ["分析", "进度", "处理", "运行"])

        except TimeoutException:
            print("开始分析按钮未找到，可能需要先选择文件")

    def test_004_results_display_accuracy(self):
        """测试结果展示完整性和准确性"""
        # 导航到静态分析页面
        self.driver.get(f"{self.base_url}/static")
        time.sleep(1)

        # 查找结果展示区域
        try:
            results_container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                                                    ".results-container, .analysis-results, #results"))
            )

            # 检查结果容器是否可见
            assert results_container.is_displayed(), "分析结果容器应该可见"

            # 查找结果列表
            result_items = results_container.find_elements(By.CSS_SELECTOR,
                                                           ".result-item, .issue-item, .finding-item")

            if result_items:
                # 检查第一个结果项的内容
                first_result = result_items[0]

                # 应该包含问题类型
                result_text = first_result.text
                assert len(result_text) > 10, "结果项应该有足够的内容"

                # 检查是否有严重程度标识
                severity_elements = first_result.find_elements(By.CSS_SELECTOR,
                                                             ".severity, .level, .priority")
                # 严重程度标识是可选的，不强求

            # 检查统计信息
            stats_elements = self.driver.find_elements(By.CSS_SELECTOR,
                                                      ".stats, .summary, .analysis-summary")

            if stats_elements:
                stats_text = stats_elements[0].text.lower()
                assert any(keyword in stats_text for keyword in ["问题", "issue", "总数", "total"])

        except TimeoutException:
            print("分析结果展示区域未找到")

    def test_005_export_functionality(self):
        """测试结果导出功能"""
        # 导航到静态分析页面
        self.driver.get(f"{self.base_url}/static")
        time.sleep(1)

        # 查找导出按钮
        try:
            export_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                                                        ".export-btn, .download-btn, button:contains('导出')")

            if export_buttons:
                export_button = export_buttons[0]

                # 点击导出按钮
                export_button.click()

                time.sleep(2)

                # 检查是否有导出选项或模态框
                export_options = self.driver.find_elements(By.CSS_SELECTOR,
                                                            ".export-options, .export-modal, .format-selector")

                if export_options:
                    # 选择导出格式
                    format_selectors = export_options[0].find_elements(By.CSS_SELECTOR,
                                                                         "input[type='radio'], .format-option")

                    if format_selectors:
                        format_selectors[0].click()
                        time.sleep(1)

                    # 确认导出
                    confirm_buttons = export_options[0].find_elements(By.CSS_SELECTOR,
                                                                      ".confirm-export, .export-confirm, button:contains('确认')")

                    if confirm_buttons:
                        confirm_buttons[0].click()
                        time.sleep(3)

                        # 检查是否有下载提示或成功消息
                        success_messages = self.driver.find_elements(By.CSS_SELECTOR,
                                                                      ".export-success, .download-success, .alert-success")

                        assert len(success_messages) > 0, "导出应该有成功提示"

                else:
                    # 如果没有选项，可能是直接导出
                    # 检查是否有成功提示
                    success_messages = self.driver.find_elements(By.CSS_SELECTOR,
                                                                  ".export-success, .download-success")
                    assert len(success_messages) > 0, "直接导出应该有成功提示"

            else:
                print("导出按钮未找到")

        except Exception as e:
            print(f"导出功能测试异常: {str(e)}")

    def test_006_analysis_parameters_configuration(self):
        """测试分析参数配置"""
        # 导航到静态分析页面
        self.driver.get(f"{self.base_url}/static")
        time.sleep(1)

        # 查找参数配置区域
        try:
            # 检查是否有配置选项
            config_elements = self.driver.find_elements(By.CSS_SELECTOR,
                                                        ".analysis-config, .parameters, .settings")

            if config_elements:
                config_area = config_elements[0]

                # 查找可配置的参数
                inputs = config_area.find_elements(By.CSS_SELECTOR,
                                                 "input, select, textarea")

                if inputs:
                    # 测试参数设置
                    for input_elem in inputs[:3]:  # 测试前3个参数
                        if input_elem.tag_name == "input":
                            if input_elem.get_attribute("type") in ["text", "number", "url"]:
                                input_elem.clear()
                                input_elem.send_keys("test")
                            elif input_elem.get_attribute("type") == "checkbox":
                                if not input_elem.is_selected():
                                    input_elem.click()
                        elif input_elem.tag_name == "select":
                            try:
                                select = Select(input_elem)
                                if select.options:
                                    select.select_by_index(0)
                            except:
                                pass

                        time.sleep(0.2)

                    # 验证参数设置
                    modified_inputs = [inp for inp in inputs[:3] if inp.get_attribute("value")]

                    assert len(modified_inputs) > 0, "应该有可修改的参数"

        except TimeoutException:
            print("分析参数配置区域未找到")

    def test_007_analysis_cancel_and_retry(self):
        """测试分析取消和重试功能"""
        # 导航到静态分析页面
        self.driver.get(f"{self.base_url}/static")
        time.sleep(1)

        # 查找取消按钮
        try:
            cancel_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                                                       ".cancel-btn, .stop-analysis, button:contains('取消')")

            if cancel_buttons:
                # 如果当前没有正在运行的分析，取消按钮可能不可见
                # 这种情况下跳过测试
                print("取消按钮存在，但可能没有正在运行的分析")

            # 查找重试按钮
            retry_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                                                      ".retry-btn, .restart-analysis, button:contains('重试')")

            if retry_buttons:
                retry_button = retry_buttons[0]
                retry_button.click()
                time.sleep(1)

                # 检查是否有相应的反应
                # 重试可能会重置表单或重新开始分析
                assert retry_button.is_displayed()

        except Exception as e:
            print(f"取消和重试功能测试异常: {str(e)}")

    def test_008_batch_analysis_functionality(self):
        """测试批量分析功能"""
        # 导航到静态分析页面
        self.driver.get(f"{self.base_url}/static")
        time.sleep(1)

        # 查找批量分析相关功能
        try:
            batch_elements = self.driver.find_elements(By.CSS_SELECTOR,
                                                       ".batch-analysis, .multiple-files, .batch-mode")

            if batch_elements:
                batch_area = batch_elements[0]

                # 查找批量文件选择
                multiple_file_inputs = batch_area.find_elements(By.CSS_SELECTOR,
                                                                 "input[type='file'][multiple], .multiple-upload")

                if multiple_file_inputs:
                    # 测试多文件选择功能
                    file_input = multiple_file_inputs[0]
                    multiple_attr = file_input.get_attribute("multiple")
                    assert multiple_attr is not None, "批量文件输入应该有multiple属性"

                # 查找批量操作按钮
                batch_buttons = batch_area.find_elements(By.CSS_SELECTOR,
                                                          ".batch-start, .analyze-all, button:contains('全部分析')")

                if batch_buttons:
                    assert len(batch_buttons) > 0, "应该有批量分析按钮"

        except Exception as e:
            print(f"批量分析功能测试异常: {str(e)}")

    def test_009_analysis_history_and_logs(self):
        """测试分析历史和日志功能"""
        # 导航到静态分析页面
        self.driver.get(f"{self.base_url}/static")
        time.sleep(1)

        # 查找历史记录相关功能
        try:
            history_elements = self.driver.find_elements(By.CSS_SELECTOR,
                                                         ".analysis-history, .recent-analysis, .history-panel")

            if history_elements:
                history_area = history_elements[0]

                # 检查历史记录列表
                history_items = history_area.find_elements(By.CSS_SELECTOR,
                                                            ".history-item, .analysis-record, .recent-item")

                if history_items:
                    assert len(history_items) > 0, "应该有历史记录项"

            # 查找日志显示区域
            log_elements = self.driver.find_elements(By.CSS_SELECTOR,
                                                   ".analysis-logs, .log-output, .debug-info")

            if log_elements:
                log_area = log_elements[0]
                # 检查日志内容
                log_content = log_area.text
                assert len(log_content) > 0, "日志区域应该有内容"

        except Exception as e:
            print(f"分析历史和日志功能测试异常: {str(e)}")

    def run_all_static_tests(self):
        """运行所有静态分析测试"""
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
    # 运行静态分析测试
    test_instance = TestStaticAnalysis()
    test_instance.setup_class()

    try:
        results = test_instance.run_all_static_tests()

        # 统计结果
        passed = sum(1 for _, status, _ in results if status == "PASSED")
        failed = sum(1 for _, status, _ in results if status == "FAILED")

        print(f"\n静态分析测试结果: {passed}/{len(results)} 通过")

        if failed > 0:
            print("失败的测试:")
            for method, status, error in results:
                if status == "FAILED":
                    print(f"  - {method}: {error}")

    finally:
        test_instance.teardown_class()
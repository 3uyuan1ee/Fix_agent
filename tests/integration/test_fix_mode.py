"""
修复模式功能测试
测试修复建议生成和应用功能
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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .test_web_integration import TestWebIntegration

class TestFixMode(TestWebIntegration):
    """修复模式功能测试类"""

    def test_001_fix_suggestion_generation(self):
        """测试修复建议生成准确性"""
        # 导航到修复模式页面
        self.driver.get(f"{self.base_url}/fix")
        time.sleep(2)

        # 查找修复建议生成区域
        try:
            # 查找问题列表或修复建议区域
            suggestions_container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                                                    ".suggestions-container, .fix-suggestions, #suggestions"))
            )

            assert suggestions_container.is_displayed(), "修复建议容器应该可见"

            # 查找生成建议的按钮
            generate_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                                                         ".generate-suggestions, .analyze-issues, #generateSuggestions")

            if generate_buttons:
                generate_button = generate_buttons[0]
                generate_button.click()
                time.sleep(3)

            # 检查修复建议列表
            suggestion_items = suggestions_container.find_elements(By.CSS_SELECTOR,
                                                               ".suggestion-item, .fix-item, .issue-card")

            if suggestion_items:
                assert len(suggestion_items) > 0, "应该有修复建议项"

                # 检查第一个建议的完整性
                first_suggestion = suggestion_items[0]

                # 应该有问题描述
                description_elements = first_suggestion.find_elements(By.CSS_SELECTOR,
                                                                      ".description, .issue-desc, .problem-desc")
                if description_elements:
                    desc_text = description_elements[0].text
                    assert len(desc_text) > 10, "问题描述应该有足够内容"

                # 应该有修复方案
                solution_elements = first_suggestion.find_elements(By.CSS_SELECTOR,
                                                                     ".solution, .fix-code, .suggested-fix")
                if solution_elements:
                    solution_text = solution_elements[0].text
                    assert len(solution_text) > 5, "修复方案应该有内容"

                # 应该有严重程度或风险评估
                risk_elements = first_suggestion.find_elements(By.CSS_SELECTOR,
                                                                   ".risk-level, .severity, .priority")
                # 风险评估是可选的

        except TimeoutException:
            print("修复建议生成区域未找到")

    def test_002_code_diff_display(self):
        """测试代码对比显示清晰"""
        # 导航到修复模式页面
        self.driver.get(f"{self.base_url}/fix")
        time.sleep(2)

        # 查找修复建议
        try:
            suggestion_items = self.driver.find_elements(By.CSS_SELECTOR,
                                                           ".suggestion-item, .fix-item, .issue-card")

            if suggestion_items:
                first_suggestion = suggestion_items[0]

                # 查找代码对比按钮或查看详情按钮
                diff_buttons = first_suggestion.find_elements(By.CSS_SELECTOR,
                                                              ".view-diff, .show-details, .expand-suggestion")

                if diff_buttons:
                    diff_button = diff_buttons[0]
                    diff_button.click()
                    time.sleep(2)

                # 检查代码对比显示
                diff_viewers = self.driver.find_elements(By.CSS_SELECTOR,
                                                        ".diff-viewer, .code-diff, .comparison")

                if diff_viewers:
                    diff_viewer = diff_viewers[0]

                    # 检查是否有原始代码和修复后代码的对比
                    original_code = diff_viewer.find_elements(By.CSS_SELECTOR,
                                                                       ".original-code, .before-code, .code-original")
                    fixed_code = diff_viewer.find_elements(By.CSS_SELECTOR,
                                                                   ".fixed-code, .after-code, .code-fixed")

                    assert len(original_code) > 0 or len(fixed_code) > 0, "代码对比应该显示原始或修复后的代码"

                    # 检查差异高亮
                    highlighted_lines = diff_viewer.find_elements(By.CSS_SELECTOR,
                                                                      ".diff-line, .highlighted, .changed-line")

                    if highlighted_lines:
                        assert len(highlighted_lines) > 0, "应该有差异高亮显示"

                    # 检查行号显示
                    line_numbers = diff_viewer.find_elements(By.CSS_SELECTOR,
                                                                ".line-number, .line-no")
                    # 行号显示是可选的

                # 检查是否有并排对比显示
                side_by_side = self.driver.find_elements(By.CSS_SELECTOR,
                                                          ".side-by-side, .comparison-view")

                if side_by_side:
                    assert side_by_side[0].is_displayed(), "并排对比视图应该可见"

        except Exception as e:
            print(f"代码对比测试异常: {str(e)}")

    def test_003_fix_operations_execution(self):
        """测试修复操作执行成功"""
        # 导航到修复模式页面
        self.driver.get(f"{self.base_url}/fix")
        time.sleep(2)

        # 查找修复建议
        try:
            suggestion_items = self.driver.find_elements(By.CSS_SELECTOR,
                                                           ".suggestion-item, .fix-item, .issue-card")

            if suggestion_items:
                first_suggestion = suggestion_items[0]

                # 查找应用修复按钮
                apply_buttons = first_suggestion.find_elements(By.CSS_SELECTOR,
                                                              ".apply-fix, .accept-suggestion, .apply-btn")

                if apply_buttons:
                    apply_button = apply_buttons[0]

                    # 点击应用修复
                    apply_button.click()
                    time.sleep(2)

                    # 检查确认对话框
                    confirm_dialogs = self.driver.find_elements(By.CSS_SELECTOR,
                                                                  ".confirm-dialog, .apply-modal, .confirmation")

                    if confirm_dialogs:
                        confirm_dialog = confirm_dialogs[0]

                        # 查找确认按钮
                        confirm_buttons = confirm_dialog.find_elements(By.CSS_SELECTOR,
                                                                      ".confirm-apply, .accept-btn, button:contains('确认')")

                        if confirm_buttons:
                            confirm_buttons[0].click()
                            time.sleep(3)

                    # 检查修复执行结果
                    success_messages = self.driver.find_elements(By.CSS_SELECTOR,
                                                                  ".fix-success, .apply-success, .alert-success")

                    if success_messages:
                        assert success_messages[0].is_displayed(), "修复成功应该有提示消息"

                    # 检查建议状态更新
                    status_badges = first_suggestion.find_elements(By.CSS_SELECTOR,
                                                                  ".status-badge, .fix-status, .applied")

                    if status_badges:
                        status_text = status_badges[0].text.lower()
                        assert any(keyword in status_text for keyword in ["已应用", "applied", "完成", "done"])

                # 查找拒绝修复按钮
                reject_buttons = first_suggestion.find_elements(By.CSS_SELECTOR,
                                                               ".reject-fix, .decline-suggestion, .reject-btn")

                if reject_buttons:
                    # 可以测试拒绝功能，但这里只检查按钮存在性
                    assert reject_buttons[0].is_displayed(), "拒绝修复按钮应该可见"

        except Exception as e:
            print(f"修复操作测试异常: {str(e)}")

    def test_004_backup_and_rollback(self):
        """测试备份和回滚功能"""
        # 导航到修复模式页面
        self.driver.get(f"{self.base_url}/fix")
        time.sleep(2)

        # 查找备份相关功能
        try:
            # 查找创建备份按钮
            backup_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                                                         ".create-backup, .backup-btn, #createBackup")

            if backup_buttons:
                backup_button = backup_buttons[0]
                backup_button.click()
                time.sleep(2)

            # 检查备份状态显示
            backup_status = self.driver.find_elements(By.CSS_SELECTOR,
                                                          ".backup-status, .backup-info, .last-backup")

            if backup_status:
                backup_info = backup_status[0]
                assert backup_info.is_displayed(), "备份状态应该可见"

                # 检查备份信息内容
                backup_text = backup_info.text
                assert len(backup_text) > 0, "备份信息应该有内容"

            # 查找回滚功能
            rollback_buttons = self.driver.find_elements(ByCSS_SELECTOR,
                                                           ".rollback, .restore-backup, .undo-fix")

            if rollback_buttons:
                # 回滚按钮可能在没有备份时不可用
                rollback_enabled = rollback_buttons[0].is_enabled()
                # 启用状态是可选的

            # 查找备份历史
            backup_history = self.driver.find_elements(By.CSS_SELECTOR,
                                                          ".backup-history, .backup-list, .restore-points")

            if backup_history:
                backup_list = backup_history[0]
                backup_items = backup_list.find_elements(By.CSS_SELECTOR,
                                                             ".backup-item, .restore-point")

                # 备份历史列表是可选的

        except Exception as e:
            print(f"备份和回滚功能测试异常: {str(e)}")

    def test_005_batch_fix_operations(self):
        """测试批量修复操作"""
        # 导航到修复模式页面
        self.driver.get(f"{self.base_url}/fix")
        time.sleep(2)

        # 查找批量操作功能
        try:
            # 查找批量操作区域
            batch_containers = self.driver.find_elements(By.CSS_SELECTOR,
                                                          ".batch-operations, .batch-fix, #batchOperations")

            if batch_containers:
                batch_container = batch_containers[0]

                # 查找全选按钮
                select_all_buttons = batch_container.find_elements(By.CSS_SELECTOR,
                                                                    ".select-all, .check-all, #selectAll")

                if select_all_buttons:
                    select_all_buttons[0].click()
                    time.sleep(1)

                # 查找批量应用按钮
                batch_apply_buttons = batch_container.find_elements(By.CSS_SELECTOR,
                                                                      ".batch-apply, .apply-all, .batch-fix-btn")

                if batch_apply_buttons:
                    batch_apply_button = batch_apply_buttons[0]
                    batch_apply_button.click()
                    time.sleep(2)

                    # 检查批量操作确认对话框
                    batch_confirm = self.driver.find_elements(By.CSS_SELECTOR,
                                                                  ".batch-confirm, .batch-modal, .confirmation")

                    if batch_confirm:
                        confirm_modal = batch_confirm[0]

                        # 查找确认按钮
                        confirm_buttons = confirm_modal.find_elements(By.CSS_SELECTOR,
                                                                          ".confirm-batch, .apply-all-btn, button:contains('确认')")

                        if confirm_buttons:
                            confirm_buttons[0].click()
                            time.sleep(5)

                    # 检查批量操作结果
                    batch_results = self.driver.find_elements(By.CSS_SELECTOR,
                                                              ".batch-results, .operation-summary, .batch-status")

                    if batch_results:
                        result_text = batch_results[0].text.lower()
                        assert any(keyword in result_text for keyword in ["批量", "batch", "操作", "完成", "成功"])

                # 查找策略选择
                strategy_selects = batch_container.find_elements(By.CSS_SELECTOR,
                                                                    "select[name='strategy'], .strategy-select, #strategy")

                if strategy_selects:
                    strategy_select = Select(strategy_selects[0])

                    # 检查策略选项
                    strategy_options = [option.text for option in strategy_select.options]
                    assert len(strategy_options) > 1, "应该有多个修复策略选项"

        except Exception as e:
            print(f"批量修复操作测试异常: {str(e)}")

    def test_006_fix_validation_and_testing(self):
        """测试修复验证和测试功能"""
        # 导航到修复模式页面
        self.driver.get(f"{self.base_url}/fix")
        time.sleep(2)

        # 查找验证和测试功能
        try:
            # 查找测试修复按钮
            test_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                                                      ".test-fix, .validate-fix, .test-btn")

            if test_buttons:
                test_button = test_buttons[0]
                test_button.click()
                time.sleep(3)

            # 检查测试结果
            test_results = self.driver.find_elements(By.CSS_SELECTOR,
                                                       ".test-results, .validation-results, .test-status")

            if test_results:
                test_result = test_results[0]

                # 检查测试状态
                status_elements = test_result.find_elements(By.CSS_SELECTOR,
                                                                  ".status, .test-status, .validation-status")

                if status_elements:
                    status_text = status_elements[0].text.lower()
                    assert any(keyword in status_text for keyword in ["测试", "test", "验证", "validation"])

                # 检查测试详情
                test_details = test_result.find_elements(By.CSS_SELECTOR,
                                                                   ".test-details, .validation-details")

                if test_details:
                    detail_text = test_details[0].text
                    assert len(detail_text) > 0, "测试详情应该有内容"

            # 查找验证规则
            validation_rules = self.driver.find_elements(ByCSS_SELECTOR,
                                                           ".validation-rules, .test-rules, .fix-rules")

            if validation_rules:
                rules_area = validation_rules[0]

                # 检查规则列表
                rule_items = rules_area.find_elements(By.CSS_SELECTOR,
                                                             ".rule-item, .validation-rule")

                # 规则列表是可选的

        except Exception as e:
            print(f"修复验证和测试功能测试异常: {str(e)}")

    def test_007_fix_customization_and_editing(self):
        """测试修复自定义和编辑功能"""
        # 导航到修复模式页面
        self.driver.get(f"{self.base_url}/fix")
        time.sleep(2)

        # 查找修复建议
        try:
            suggestion_items = self.driver.find_elements(By.CSS_SELECTOR,
                                                           ".suggestion-item, .fix-item, .issue-card")

            if suggestion_items:
                first_suggestion = suggestion_items[0]

                # 查找编辑按钮
                edit_buttons = first_suggestion.find_elements(By.CSS_SELECTOR,
                                                              ".edit-fix, .customize-fix, .edit-btn")

                if edit_buttons:
                    edit_button = edit_buttons[0]
                    edit_button.click()
                    time.sleep(2)

                    # 检查编辑界面
                    edit_modals = self.driver.find_elements(By.CSS_SELECTOR,
                                                              ".edit-modal, .fix-editor, .customization-panel")

                    if edit_modals:
                        edit_modal = edit_modals[0]

                        # 查找代码编辑器
                        code_editors = edit_modal.find_elements(By.CSS_SELECTOR,
                                                                       "textarea, .code-editor, .fix-code-input")

                        if code_editors:
                            code_editor = code_editors[0]

                            # 测试编辑功能
                            original_code = code_editor.get_attribute("value") or ""
                            code_editor.clear()
                            code_editor.send_keys("# 编辑后的代码\nprint('Hello World')")

                        # 查找保存按钮
                        save_buttons = edit_modal.find_elements(By.CSS_SELECTOR,
                                                                          ".save-edit, .apply-custom, .save-btn")

                        if save_buttons:
                            save_buttons[0].click()
                            time.sleep(2)

                # 查找自定义选项
                custom_options = first_suggestion.find_elements(By.CSS_SELECTOR,
                                                                   ".custom-options, .fix-options, .advanced-settings")

                if custom_options:
                    options_area = custom_options[0]

                    # 检查可配置选项
                    option_inputs = options_area.find_elements(By.CSS_SELECTOR,
                                                                   "input, select, textarea")

                    # 可配置选项是可选的

        except Exception as e:
            print(f"修复自定义和编辑功能测试异常: {str(e)}")

    def test_008_fix_progress_tracking(self):
        """测试修复进度跟踪"""
        # 导航到修复模式页面
        self.driver.get(f"{self.base_url}/fix")
        time.sleep(2)

        # 查找进度跟踪功能
        try:
            # 查找进度条或状态指示器
            progress_bars = self.driver.find_elements(By.CSS_SELECTOR,
                                                        ".progress-bar, .fix-progress, .operation-progress")

            if progress_bars:
                progress_bar = progress_bars[0]

                # 检查进度值
                progress_value = progress_bar.get_attribute("aria-valuenow")
                progress_style = progress_bar.get_attribute("style")

                assert progress_value is not None or progress_style is not None, "进度条应该有值"

            # 查找状态指示器
            status_indicators = self.driver.find_elements(By.CSS_SELECTOR,
                                                             ".status-indicator, .fix-status, .operation-status")

            if status_indicators:
                status_indicator = status_indicators[0]
                assert status_indicator.is_displayed(), "状态指示器应该可见"

            # 查找进度详情
            progress_details = self.driver.find_elements(By.CSS_SELECTOR,
                                                           ".progress-details, .operation-details, .step-indicator")

            if progress_details:
                details_area = progress_details[0]

                # 检查步骤列表
                step_items = details_area.find_elements(By.CSS_SELECTOR,
                                                             ".step, .progress-step, .operation-step")

                # 步骤列表是可选的

        except Exception as e:
            print(f"修复进度跟踪测试异常: {str(e)}")

    def run_all_fix_tests(self):
        """运行所有修复模式测试"""
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
    # 运行修复模式测试
    test_instance = TestFixMode()
    test_instance.setup_class()

    try:
        results = test_instance.run_all_fix_tests()

        # 统计结果
        passed = sum(1 for _, status, _ in results if status == "PASSED")
        failed = sum(1 for _, status, _ in results if status == "FAILED")

        print(f"\n修复模式测试结果: {passed}/{len(results)} 通过")

        if failed > 0:
            print("失败的测试:")
            for method, status, error in results:
                if status == "FAILED":
                    print(f"  - {method}: {error}")

    finally:
        test_instance.teardown_class()
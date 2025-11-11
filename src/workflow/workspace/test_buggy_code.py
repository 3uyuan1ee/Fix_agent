"""
针对buggy_code.py的全面测试用例
验证修复的有效性、健壮性和安全性
"""

import os
import sys
from typing import List, Union

# 导入被测试的模块
import buggy_code
import pytest


class TestCalculateAverage:
    """测试calculate_average函数"""

    def test_normal_numbers(self):
        """测试正常数字列表"""
        numbers = [1, 2, 3, 4, 5]
        result = buggy_code.calculate_average(numbers)
        assert result == 3.0

    def test_negative_numbers(self):
        """测试负数列表"""
        numbers = [-1, -2, -3, -4, -5]
        result = buggy_code.calculate_average(numbers)
        assert result == -3.0

    def test_float_numbers(self):
        """测试浮点数列表"""
        numbers = [1.5, 2.5, 3.5]
        result = buggy_code.calculate_average(numbers)
        assert result == 2.5

    def test_mixed_numbers(self):
        """测试整数和浮点数混合列表"""
        numbers = [1, 2.5, 3, 4.5]
        result = buggy_code.calculate_average(numbers)
        assert result == 2.75

    def test_single_number(self):
        """测试单个数字"""
        numbers = [42]
        result = buggy_code.calculate_average(numbers)
        assert result == 42.0

    def test_zero_numbers(self):
        """测试包含0的列表"""
        numbers = [0, 0, 0, 0]
        result = buggy_code.calculate_average(numbers)
        assert result == 0.0

    def test_large_numbers(self):
        """测试大数字"""
        numbers = [1000000, 2000000, 3000000]
        result = buggy_code.calculate_average(numbers)
        assert result == 2000000.0

    def test_empty_list(self):
        """测试空列表 - 应该抛出ValueError"""
        with pytest.raises(ValueError, match="列表不能为空"):
            buggy_code.calculate_average([])

    def test_non_list_input(self):
        """测试非列表输入 - 应该抛出ValueError"""
        with pytest.raises(ValueError, match="输入必须是一个列表"):
            buggy_code.calculate_average("not a list")

        with pytest.raises(ValueError, match="输入必须是一个列表"):
            buggy_code.calculate_average(123)

        with pytest.raises(ValueError, match="输入必须是一个列表"):
            buggy_code.calculate_average({"key": "value"})

    def test_list_with_non_numeric(self):
        """测试包含非数字元素的列表 - 应该抛出ValueError"""
        with pytest.raises(ValueError, match="列表包含非数字元素"):
            buggy_code.calculate_average([1, 2, "three", 4])

        with pytest.raises(ValueError, match="列表包含非数字元素"):
            buggy_code.calculate_average([1, 2, [3], 4])

        with pytest.raises(ValueError, match="列表包含非数字元素"):
            buggy_code.calculate_average([1, 2, None, 4])

        with pytest.raises(ValueError, match="列表包含非数字元素"):
            buggy_code.calculate_average([1, 2, True, 4])

    def test_list_with_string_numbers(self):
        """测试包含字符串数字的列表 - 应该抛出ValueError"""
        with pytest.raises(ValueError, match="列表包含非数字元素"):
            buggy_code.calculate_average(["1", "2", "3"])

    def test_performance_large_list(self):
        """测试大列表性能"""
        large_list = list(range(10000))
        result = buggy_code.calculate_average(large_list)
        assert result == 4999.5


class TestProcessData:
    """测试process_data函数"""

    def test_normal_string(self):
        """测试正常字符串"""
        data = "  hello world  "
        result = buggy_code.process_data(data)
        assert result == "处理后的数据: hello world"

    def test_empty_string(self):
        """测试空字符串"""
        data = ""
        result = buggy_code.process_data(data)
        assert result == "处理后的数据: "

    def test_whitespace_only(self):
        """测试只有空格的字符串"""
        data = "   "
        result = buggy_code.process_data(data)
        assert result == "处理后的数据: "

    def test_string_with_newlines(self):
        """测试包含换行符的字符串"""
        data = "hello\nworld"
        result = buggy_code.process_data(data)
        assert result == "处理后的数据: hello\nworld"

    def test_string_with_tabs(self):
        """测试包含制表符的字符串"""
        data = "hello\tworld"
        result = buggy_code.process_data(data)
        assert result == "处理后的数据: hello\tworld"

    def test_non_string_input(self):
        """测试非字符串输入 - 应该抛出ValueError"""
        with pytest.raises(ValueError, match="输入数据必须是字符串"):
            buggy_code.process_data(123)

        with pytest.raises(ValueError, match="输入数据必须是字符串"):
            buggy_code.process_data([1, 2, 3])

        with pytest.raises(ValueError, match="输入数据必须是字符串"):
            buggy_code.process_data({"key": "value"})

        with pytest.raises(ValueError, match="输入数据必须是字符串"):
            buggy_code.process_data(None)

    def test_unicode_string(self):
        """测试Unicode字符串"""
        data = "你好，世界！"
        result = buggy_code.process_data(data)
        assert result == "处理后的数据: 你好，世界！"

    def test_special_characters(self):
        """测试特殊字符"""
        data = "!@#$%^&*()"
        result = buggy_code.process_data(data)
        assert result == "处理后的数据: !@#$%^&*()"


class TestMainFunction:
    """测试main函数"""

    def test_main_normal_execution(self):
        """测试main函数正常执行"""
        # 重定向stdout以捕获输出
        import io

        captured_output = io.StringIO()

        # 由于main函数中有sys.exit，我们需要模拟退出
        original_exit = sys.exit
        exit_codes = []

        def mock_exit(code):
            exit_codes.append(code)

        sys.exit = mock_exit

        try:
            # 由于main函数会打印输出，我们需要重定向
            original_stdout = sys.stdout
            sys.stdout = captured_output

            # 执行main函数
            result = buggy_code.main()

            sys.stdout = original_stdout
        finally:
            sys.exit = original_exit

        # 检查退出代码
        assert exit_codes == [0] or result == 0

    def test_main_with_exception(self):
        """测试main函数异常处理"""
        # 测试当发生异常时的处理
        # 由于main函数内部有try-catch，我们需要确保它能正确处理异常
        # 这里我们通过修改函数来测试异常处理
        original_calculate_average = buggy_code.calculate_average

        def mock_calculate_average(numbers):
            if numbers == [1, 2, 3, 4, 5]:
                raise Exception("模拟异常")
            return original_calculate_average(numbers)

        buggy_code.calculate_average = mock_calculate_average

        try:
            # 重定向stdout以捕获输出
            import io

            captured_output = io.StringIO()
            original_stdout = sys.stdout
            sys.stdout = captured_output

            # 执行main函数
            result = buggy_code.main()

            sys.stdout = original_stdout

            # 应该捕获异常并返回1
            assert result == 1

        finally:
            # 恢复原始函数
            buggy_code.calculate_average = original_calculate_average


class TestEdgeCases:
    """测试边界情况"""

    def test_calculate_average_with_inf(self):
        """测试包含无穷大的情况"""
        import math

        numbers = [1, 2, float("inf")]
        result = buggy_code.calculate_average(numbers)
        assert math.isinf(result)

    def test_calculate_average_with_nan(self):
        """测试包含NaN的情况"""
        import math

        numbers = [1, 2, float("nan")]
        result = buggy_code.calculate_average(numbers)
        assert math.isnan(result)

    def test_process_data_with_very_long_string(self):
        """测试处理超长字符串"""
        long_string = "a" * 1000000
        result = buggy_code.process_data(long_string)
        assert len(result) == len("处理后的数据: ") + 1000000

    def test_calculate_average_with_very_large_list(self):
        """测试超大列表"""
        large_list = list(range(100000))
        result = buggy_code.calculate_average(large_list)
        assert result == 49999.5


class TestSecurity:
    """测试安全性"""

    def test_no_code_injection_in_process_data(self):
        """测试process_data函数不会执行代码注入"""
        # 测试字符串中包含可能危险的字符
        dangerous_strings = [
            "__import__('os').system('ls')",
            "exec('print(\"dangerous\")')",
            "eval('1+1')",
            "open('file.txt', 'w')",
            "import os",
            "subprocess.run(['ls'])",
        ]

        for dangerous_str in dangerous_strings:
            # 应该正常处理，不会执行代码
            result = buggy_code.process_data(dangerous_str)
            assert isinstance(result, str)
            assert "处理后的数据:" in result

    def test_input_validation_prevents_injection(self):
        """测试输入验证防止注入攻击"""
        # 测试各种可能的输入攻击
        attack_inputs = [
            None,
            [],
            {},
            123,
            3.14,
            True,
            False,
            lambda x: x,
            object(),
        ]

        for attack_input in attack_inputs:
            if not isinstance(attack_input, str):
                with pytest.raises(ValueError):
                    buggy_code.process_data(attack_input)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

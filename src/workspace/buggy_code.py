# 修复后的代码示例
import os
import sys


def calculate_average(numbers_list):
    """
    计算数字列表的平均值
    Args:
        numbers_list: 数字列表
    Returns:
        float: 平均值
    Raises:
        ValueError: 当列表为空或包含非数字元素时
    """
    # 检查输入是否为列表
    if not isinstance(numbers_list, list):
        raise ValueError("输入必须是一个列表")

    # 检查列表是否为空
    if len(numbers_list) == 0:
        raise ValueError("列表不能为空")

    # 检查所有元素是否为数字
    for num in numbers_list:
        if not isinstance(num, (int, float)):
            raise ValueError(f"列表包含非数字元素: {num}")

    total = 0
    for num in numbers_list:
        total += num
    average = total / len(numbers_list)
    return average


def process_data(data):
    """
    处理输入数据
    Args:
        data: 要处理的数据
    Returns:
        str: 处理结果
    """
    # 验证输入数据
    if not isinstance(data, str):
        raise ValueError("输入数据必须是字符串")

    # 移除前后空格
    processed_data = data.strip()

    # 添加处理逻辑
    result = f"处理后的数据: {processed_data}"
    print(result)
    return result


def main():
    try:
        # 测试正常情况
        numbers = [1, 2, 3, 4, 5]
        avg = calculate_average(numbers)
        print(f"平均值: {avg}")

        # 测试数据处理函数
        process_result = process_data("test")
        print(f"处理结果: {process_result}")

        # 测试空列表情况（应该抛出异常）
        try:
            empty_numbers = []
            avg_empty = calculate_average(empty_numbers)
            print(f"空列表平均值: {avg_empty}")
        except ValueError as e:
            print(f"空列表处理错误: {e}")

        # 测试非数字元素情况
        try:
            invalid_numbers = [1, 2, "three", 4]
            avg_invalid = calculate_average(invalid_numbers)
            print(f"无效数字列表平均值: {avg_invalid}")
        except ValueError as e:
            print(f"无效数字列表处理错误: {e}")

    except Exception as e:
        print(f"程序运行时发生错误: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

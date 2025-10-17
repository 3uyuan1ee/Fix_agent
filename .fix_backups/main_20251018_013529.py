#!/usr/bin/env python3
"""
主程序入口 - 包含多个需要修复的问题
"""

import os
import sys
from utils import *  # 通配符导入
import json

def main():
    # 硬编码密码 - 安全问题
    password = "admin123"
    api_key = "sk-1234567890abcdef"

    # 使用未定义的变量
    result = x + y

    # 数据库连接未关闭
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER, name TEXT)")

    # 可能的SQL注入风险
    user_input = input("请输入用户名: ")
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    cursor.execute(query)

    # 未使用的变量
    unused_var = "This is not used"
    another_unused = 42

    # 可能的性能问题
    result = []
    for i in range(1000):
        for j in range(1000):
            result.append(i * j)

    print("程序执行完成")
    return result

if __name__ == "__main__":
    main()
        
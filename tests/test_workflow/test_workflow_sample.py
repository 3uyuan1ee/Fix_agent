# 测试文件 - 用于工作流验证
import os
import sqlite3

def get_user_by_id(user_id):
    """根据用户ID获取用户信息"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # 存在SQL注入风险的代码
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)

    user = cursor.fetchone()
    conn.close()
    return user

def process_user_data(user_input):
    """处理用户数据"""
    # 未经验证的输入处理
    data = eval(user_input)  # 存在安全风险
    return data

def unused_function():
    """未被使用的函数"""
    x = 1 + 1
    return x

# 缺少文档的函数
def calculate(a, b):
    return a + b

if __name__ == "__main__":
    user = get_user_by_id(1)
    print(user)
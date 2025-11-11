# 修复后的项目代码
class UserManager:
    def __init__(self):
        self.users = {}

    def add_user(self, name, age):
        """
        添加用户到管理器
        Args:
            name: 用户名
            age: 用户年龄
        Raises:
            ValueError: 当参数无效时
        """
        # 参数验证
        if not isinstance(name, str) or not name.strip():
            raise ValueError("用户名必须是有效的字符串")

        if not isinstance(age, int) or age <= 0 or age > 150:
            raise ValueError("年龄必须是1到150之间的整数")

        # 检查用户名是否已存在
        if name in self.users:
            raise ValueError(f"用户 '{name}' 已存在")

        self.users[name] = age

    def get_average_age(self):
        """
        计算所有用户的平均年龄
        Returns:
            float: 平均年龄
        Raises:
            ValueError: 当没有用户时
        """
        if len(self.users) == 0:
            raise ValueError("没有用户数据，无法计算平均年龄")

        total = sum(self.users.values())
        return total / len(self.users)

    def find_oldest_user(self):
        """
        找到最年长的用户
        Returns:
            tuple: (用户名, 年龄)
        Raises:
            ValueError: 当没有用户时
        """
        if len(self.users) == 0:
            raise ValueError("没有用户数据，无法找到最年长用户")

        oldest_name = max(self.users, key=self.users.get)
        return oldest_name, self.users[oldest_name]

    def get_user_count(self):
        """
        获取用户数量
        Returns:
            int: 用户数量
        """
        return len(self.users)

    def get_user_info(self, name):
        """
        获取指定用户的信息
        Args:
            name: 用户名
        Returns:
            dict: 用户信息
        Raises:
            ValueError: 当用户不存在时
        """
        if name not in self.users:
            raise ValueError(f"用户 '{name}' 不存在")

        return {"name": name, "age": self.users[name]}


def main():
    try:
        manager = UserManager()

        # 测试添加用户
        manager.add_user("张三", 25)
        manager.add_user("李四", 30)
        manager.add_user("王五", 28)

        print(f"当前用户数量: {manager.get_user_count()}")

        # 测试获取平均年龄
        avg = manager.get_average_age()
        print(f"平均年龄: {avg:.2f}")

        # 测试找到最年长用户
        oldest_name, oldest_age = manager.find_oldest_user()
        print(f"最年长用户: {oldest_name}, 年龄: {oldest_age}")

        # 测试获取用户信息
        user_info = manager.get_user_info("张三")
        print(f"张三的信息: {user_info}")

        # 测试错误情况
        try:
            manager.add_user("", 25)  # 空用户名
        except ValueError as e:
            print(f"添加空用户名错误: {e}")

        try:
            manager.add_user("李四", 200)  # 无效年龄
        except ValueError as e:
            print(f"添加无效年龄错误: {e}")

        try:
            manager.add_user("张三", 25)  # 重复用户
        except ValueError as e:
            print(f"添加重复用户错误: {e}")

        try:
            empty_manager = UserManager()
            empty_avg = empty_manager.get_average_age()  # 空管理器
        except ValueError as e:
            print(f"空管理器平均年龄错误: {e}")

        try:
            empty_manager.find_oldest_user()  # 空管理器
        except ValueError as e:
            print(f"空管理器最年长用户错误: {e}")

        try:
            manager.get_user_info("不存在的用户")  # 不存在的用户
        except ValueError as e:
            print(f"获取不存在用户错误: {e}")

    except Exception as e:
        print(f"程序运行时发生错误: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    import sys

    sys.exit(exit_code)

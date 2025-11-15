"""
导入助手

提供统一的导入函数来处理不同的导入场景。
"""

def safe_import(module_path: str, fallback_paths: list = None):
    """
    安全的导入函数

    Args:
        module_path: 要导入的模块路径
        fallback_paths: 备用导入路径列表

    Returns:
        模块对象或None
    """
    if fallback_paths is None:
        fallback_paths = []

    # 尝试直接导入
    try:
        module = __import__(module_path)
        return module
    except ImportError:
        pass

    # 尝试从当前包导入
    try:
        return __import__(module_path, fromlist=[module_path.split('.')[-1]])
    except ImportError:
        pass

    # 尝试备用路径
    for fallback_path in fallback_paths:
        try:
            return __import__(fallback_path)
        except ImportError:
            continue

    return None

def safe_relative_import(module_path: str, relative_to: str = None):
    """
    安全的相对导入函数

    Args:
        module_path: 要导入的模块路径
        relative_to: 相对于哪个模块

    Returns:
        模块对象或None
    """
    if relative_to:
        full_path = f"{relative_to}.{module_path}"
        try:
            return __import__(full_path, fromlist=[module_path])
        except ImportError:
            pass

    # 尝试直接导入
    try:
        return __import__(module_path, fromlist=[module_path])
    except ImportError:
        pass

    return None
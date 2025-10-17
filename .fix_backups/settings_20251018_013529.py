"""配置模块 - 包含硬编码敏感信息"""

# 硬编码的API密钥 - 安全问题
API_KEY = "sk-1234567890abcdef"
DATABASE_URL = "sqlite:///app.db"
PASSWORD = "secretpassword"

# 敏感配置信息
EMAIL_PASSWORD = "email123"
SECRET_KEY = "insecure-secret-key"

def get_config():
    config = {
        'api_key': API_KEY,
        'database_url': DATABASE_URL,
        'password': PASSWORD
    }
    return config

# 配置验证
def validate_config():
    if not API_KEY:
        raise ValueError("API密钥未配置")
    if not DATABASE_URL:
        raise ValueError("数据库URL未配置")
    return True
        
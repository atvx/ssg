from pydantic_settings import BaseSettings
from typing import Optional, List, Dict, Any, ClassVar
import os
from pathlib import Path
from dotenv import load_dotenv

# 确保能找到.env文件
base_dir = Path(__file__).resolve().parent.parent
env_path = base_dir / '.env'

# 修改load_dotenv调用，设置override=True强制覆盖已存在的环境变量
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path), verbose=True, override=True)
    print(f"已加载环境变量文件: {env_path}")
else:
    print(f"警告: 环境变量文件不存在: {env_path}")

def process_url(url):
    """处理URL字符串，移除可能的引号"""
    if url and isinstance(url, str):
        url = url.strip()
        if url.startswith('"') and url.endswith('"'):
            url = url[1:-1]
        return url
    return url


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "销售数据获取系统"
    API_V1_STR: str = "/api"
    DEBUG: bool = True
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "QIAN")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # 文件上传配置
    UPLOAD_DRIVER: str = os.getenv("UPLOAD_DRIVER", "r2")
    APP_DOMAIN: str = os.getenv("APP_DOMAIN", "https://example.com")
    MEDIA_PREFIX: str = os.getenv("MEDIA_PREFIX", "/media")
    
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+pymysql://qian:qian163@124.221.92.150:3306/ssgmlj?connect_timeout=10")
    
    # Redis配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://:163000@124.221.92.150:6378/0")
    
    # Celery配置
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://:163000@124.221.92.150:6378/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://:163000@124.221.92.150:6378/0")
    
    # 美团POS配置
    MEITUAN_CONFIG: Dict[str, str] = {
        "LOGIN_URL": "https://pos.meituan.com/web/rms-account#/login",
        "BUSINESS_OVERVIEW_URL": "https://pos.meituan.com/web/report/business-report#/rms-report/business-report",
        "PHONE_NUMBER": os.getenv("MEITUAN_PHONE", ""),
        "TARGET_ORG": os.getenv("MEITUAN_ORG", ""),
    }
    
    # 滑块验证模式: 0=自动, 1=手动
    SLIDER_VERIFY_MODE: int = int(os.getenv("SLIDER_VERIFY_MODE", "0"))
    
    # 登录方式: 0=手机号登录, 1=账号登录
    LOGIN_MODE: int = int(os.getenv("LOGIN_MODE", "1"))
    
    # 账号登录信息
    ACCOUNT_CONFIG: Dict[str, str] = {
        "USERNAME": os.getenv("MEITUAN_USERNAME", ""),
        "PASSWORD": os.getenv("MEITUAN_PASSWORD", "")
    }
    
    # 多维系统配置
    DUOWEI_CONFIG: Dict[str, str] = {
        "BASE_URL": os.getenv("DUOWEI_BASE_URL", "http://saas.wxdw.top:8899/web_api"),
        "USER_ID": os.getenv("DUOWEI_USER_ID", "00016"),
        "DB_NAME": os.getenv("DUOWEI_DB_NAME", "ssgmlj"),
    }
    
    # 浏览器配置
    HEADLESS: bool = os.getenv("HEADLESS", "True").lower() in ("true", "1", "t")
    CHROME_USER_DATA_DIR: str = os.getenv("CHROME_USER_DATA_DIR", os.path.join(base_dir, "edge_user_data"))
    EDGE_USER_DATA_DIR: str = os.getenv("EDGE_USER_DATA_DIR", os.path.join(base_dir, "edge_user_data"))

    # Selenium-Wire配置
    SELENIUM_WIRE_OPTIONS: Dict[str, Any] = {
        'disable_encoding': True,  # 禁用内容编码，以便能够读取响应体
        'suppress_connection_errors': True,  # 抑制连接错误
        'verify_ssl': False,  # 不验证SSL证书，避免某些HTTPS请求问题
        'request_storage': 'memory',  # 使用内存存储请求，提高性能
        'request_storage_max_size': 50,  # 降低存储的请求数量以节省内存
        'connection_timeout': 60,  # 连接超时时间
        'connection_keep_alive': True,  # 保持连接
        'max_retries': 3,  # 最大重试次数
        'http2': False  # 禁用HTTP/2协议，避免StreamClosedError错误
    }

    # 网络超时配置
    NETWORK_TIMEOUT: int = int(os.getenv("NETWORK_TIMEOUT", "60"))  # 默认60秒
    API_MONITOR_TIMEOUT: int = int(os.getenv("API_MONITOR_TIMEOUT", "90"))  # 默认90秒
    API_RETRY_TIMEOUT: int = int(os.getenv("API_RETRY_TIMEOUT", "30"))  # 重试时的超时时间，默认30秒
    MAX_API_RETRIES: int = int(os.getenv("MAX_API_RETRIES", "2"))  # 最大重试次数，默认2次


# 打印环境变量值以进行调试
headless_env = os.getenv("HEADLESS")
# print(f"环境变量 HEADLESS={headless_env}")

settings = Settings()

# 打印最终HEADLESS设置值
# print(f"最终HEADLESS设置: {settings.HEADLESS}")

# 导出常用配置变量，以支持直接导入
MEITUAN_CONFIG = settings.MEITUAN_CONFIG
DUOWEI_CONFIG = settings.DUOWEI_CONFIG
ACCOUNT_CONFIG = settings.ACCOUNT_CONFIG
SLIDER_VERIFY_MODE = settings.SLIDER_VERIFY_MODE
LOGIN_MODE = settings.LOGIN_MODE
DATABASE_URL = settings.DATABASE_URL
REDIS_URL = settings.REDIS_URL
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
UPLOAD_DRIVER = settings.UPLOAD_DRIVER
APP_DOMAIN = settings.APP_DOMAIN
MEDIA_PREFIX = settings.MEDIA_PREFIX
SELENIUM_WIRE_OPTIONS = settings.SELENIUM_WIRE_OPTIONS

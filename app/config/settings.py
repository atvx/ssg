from pydantic_settings import BaseSettings
from typing import Optional, List, Dict, Any, ClassVar
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "销售数据获取系统"
    API_V1_STR: str = "/api"
    DEBUG: bool = True
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-for-development-only")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+pymysql://root:Qian1202#@124.221.92.150:3306/ssgmlj")
    
    # Redis配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Celery配置
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    # 美团POS配置
    MEITUAN_CONFIG: Dict[str, str] = {
        "LOGIN_URL": "https://pos.meituan.com/web/rms-account#/login",
        "BUSINESS_OVERVIEW_URL": "https://pos.meituan.com/web/rms-report/#/business-overview",
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
    CHROME_USER_DATA_DIR: str = "chrome_user_data"
    HEADLESS: bool = os.getenv("HEADLESS", "False").lower() == "true"


settings = Settings()

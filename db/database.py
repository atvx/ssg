from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import settings
import os
from sqlalchemy.pool import QueuePool
import logging

# 设置日志
logger = logging.getLogger(__name__)

# 获取数据库URL
DATABASE_URL = settings.DATABASE_URL

logger.info(f"使用的数据库URL: {DATABASE_URL}")

# MySQL数据库连接配置
engine = create_engine(
    DATABASE_URL,
    pool_size=5,  # 连接池大小
    max_overflow=10,  # 允许的最大溢出连接数
    pool_timeout=30,  # 获取连接的超时时间
    pool_recycle=3600,  # 连接回收时间（秒）
    pool_pre_ping=True  # 使用ping测试连接是否有效
)
logger.info("已配置MySQL数据库连接")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# 依赖函数，在FastAPI的依赖注入系统中使用
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

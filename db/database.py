from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import settings
import os

# 确保URL格式正确
DATABASE_URL = settings.DATABASE_URL

# 如果URL为空，使用默认值
if not DATABASE_URL:
    DATABASE_URL = "mysql+pymysql://qian:qian163@124.221.92.150:3306/ssgmlj"

# print(f"使用的数据库URL: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# 依赖函数，在FastAPI的依赖注入系统中使用
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

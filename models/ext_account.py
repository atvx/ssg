from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from db.database import Base

class ExtAccount(Base):
    """外部第三方平台账号模型"""
    __tablename__ = "ext_accounts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="自增主键")
    user_id = Column(Integer, nullable=False, index=True, comment="关联的用户ID")
    platform = Column(String(50), nullable=False, comment="第三方平台名称 (e.g., meituan, duowei, wechat)")
    username = Column(String(200), nullable=False, comment="用户名")
    password = Column(String(255), nullable=False, comment="密码")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间") 
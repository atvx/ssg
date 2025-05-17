from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.database import Base


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_type = Column(String(50), nullable=False)  # "fetch_meituan", "fetch_duowei", "fetch_all"
    status = Column(String(20), nullable=False)  # "pending", "running", "completed", "failed"
    progress = Column(Integer, default=0)
    result = Column(Text)  # 存储JSON格式的结果
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # 与用户表关联
    user = relationship("User", back_populates="tasks")

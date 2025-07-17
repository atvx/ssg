from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from db.database import Base


class Task(Base):
    """任务模型"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(50), index=True)
    status = Column(String(20), default="pending", index=True)
    progress = Column(Integer, default=0)
    params = Column(JSON, nullable=True)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="tasks")


class TaskScheduleConfig(Base):
    """任务调度配置模型"""
    __tablename__ = "task_schedule_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True, unique=True)
    description = Column(String(255), nullable=True)
    task_type = Column(String(50), nullable=False)  # 对应的任务类型
    schedule_type = Column(String(20), nullable=False)  # crontab 或 interval
    
    # crontab格式配置
    minute = Column(String(20), default="*")
    hour = Column(String(20), default="*")
    day_of_week = Column(String(20), default="*")
    day_of_month = Column(String(20), default="*")
    month_of_year = Column(String(20), default="*")
    
    # interval格式配置（秒为单位）
    interval_seconds = Column(Integer, default=0)
    
    # 时间段配置
    start_time = Column(String(8), nullable=True)  # 格式: HH:MM:SS
    end_time = Column(String(8), nullable=True)    # 格式: HH:MM:SS
    
    enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "schedule_type": self.schedule_type,
            "minute": self.minute,
            "hour": self.hour,
            "day_of_week": self.day_of_week,
            "day_of_month": self.day_of_month,
            "month_of_year": self.month_of_year,
            "interval_seconds": self.interval_seconds,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "enabled": self.enabled,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

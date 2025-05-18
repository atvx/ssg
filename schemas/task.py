from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime


class TaskBase(BaseModel):
    """任务基础模型"""
    task_type: str = Field(..., description="任务类型")


class TaskCreate(TaskBase):
    """任务创建模型"""
    pass


class TaskUpdate(BaseModel):
    """任务更新模型"""
    status: Optional[str] = Field(None, description="任务状态")
    progress: Optional[int] = Field(None, description="任务进度")
    result: Optional[str] = Field(None, description="任务结果")
    error: Optional[str] = Field(None, description="错误信息")
    completed_at: Optional[datetime] = Field(None, description="完成时间")


class Task(TaskBase):
    """任务完整模型"""
    id: int = Field(..., description="任务ID")
    user_id: int = Field(..., description="用户ID")
    status: str = Field(..., description="任务状态")
    progress: int = Field(..., description="任务进度")
    result: Optional[str] = Field(None, description="任务结果")
    error: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")

    class Config:
        orm_mode = True


class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: int = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    result: Optional[str] = Field(None, description="任务结果")

    class Config:
        orm_mode = True

from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime


class TaskBase(BaseModel):
    task_type: str


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[int] = None
    result: Optional[str] = None
    error: Optional[str] = None
    completed_at: Optional[datetime] = None


class Task(TaskBase):
    id: int
    user_id: int
    status: str
    progress: int
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskStatus(BaseModel):
    id: int
    status: str
    progress: int

from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from datetime import datetime


class TaskBase(BaseModel):
    """任务基础模型"""
    task_type: str = Field(..., description="任务类型")
    params: Optional[Dict[str, Any]] = Field(None, description="任务参数，如查询日期等")


class TaskCreate(TaskBase):
    """任务创建模型"""
    pass


class TaskUpdate(BaseModel):
    """任务更新模型"""
    status: Optional[str] = Field(None, description="任务状态")
    progress: Optional[int] = Field(None, description="任务进度")
    result: Optional[str] = Field(None, description="任务结果")
    error: Optional[str] = Field(None, description="错误信息")


class Task(TaskBase):
    """任务完整模型"""
    id: int = Field(..., description="任务ID")
    user_id: int = Field(..., description="用户ID")
    status: str = Field(..., description="任务状态")
    progress: int = Field(..., description="任务进度")
    result: Optional[str] = Field(None, description="任务结果")
    error: Optional[str] = Field(None, description="错误信息")
    params: Optional[str] = Field(None, description="任务参数，存储为JSON字符串")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: int = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    result: Optional[str] = Field(None, description="任务结果")
    params: Optional[str] = Field(None, description="任务参数")

    class Config:
        from_attributes = True


# 新增的调度配置相关模型
class TaskScheduleConfigBase(BaseModel):
    """任务调度配置基础模型"""
    name: str = Field(..., description="配置名称")
    description: Optional[str] = Field(None, description="配置描述")
    task_type: str = Field(..., description="任务类型")
    schedule_type: str = Field(..., description="调度类型(crontab或interval)")
    
    # crontab格式配置
    minute: Optional[str] = Field("*", description="分钟 (crontab格式)")
    hour: Optional[str] = Field("*", description="小时 (crontab格式)")
    day_of_week: Optional[str] = Field("*", description="星期几 (crontab格式)")
    day_of_month: Optional[str] = Field("*", description="日期 (crontab格式)")
    month_of_year: Optional[str] = Field("*", description="月份 (crontab格式)")
    
    # interval格式配置
    interval_seconds: Optional[int] = Field(0, description="间隔秒数 (interval格式)")
    
    # 时间段配置
    start_time: Optional[str] = Field(None, description="开始时间 (HH:MM:SS)")
    end_time: Optional[str] = Field(None, description="结束时间 (HH:MM:SS)")
    
    enabled: bool = Field(True, description="是否启用")


class TaskScheduleConfigCreate(TaskScheduleConfigBase):
    """创建任务调度配置"""
    pass


class TaskScheduleConfigUpdate(BaseModel):
    """更新任务调度配置"""
    name: Optional[str] = Field(None, description="配置名称")
    description: Optional[str] = Field(None, description="配置描述")
    task_type: Optional[str] = Field(None, description="任务类型")
    schedule_type: Optional[str] = Field(None, description="调度类型(crontab或interval)")
    
    # crontab格式配置
    minute: Optional[str] = Field(None, description="分钟 (crontab格式)")
    hour: Optional[str] = Field(None, description="小时 (crontab格式)")
    day_of_week: Optional[str] = Field(None, description="星期几 (crontab格式)")
    day_of_month: Optional[str] = Field(None, description="日期 (crontab格式)")
    month_of_year: Optional[str] = Field(None, description="月份 (crontab格式)")
    
    # interval格式配置
    interval_seconds: Optional[int] = Field(None, description="间隔秒数 (interval格式)")
    
    # 时间段配置
    start_time: Optional[str] = Field(None, description="开始时间 (HH:MM:SS)")
    end_time: Optional[str] = Field(None, description="结束时间 (HH:MM:SS)")
    
    enabled: Optional[bool] = Field(None, description="是否启用")


class TaskScheduleConfig(TaskScheduleConfigBase):
    """任务调度配置响应模型"""
    id: int
    last_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TaskScheduleConfigList(BaseModel):
    """任务调度配置列表响应模型"""
    total: int
    items: List[TaskScheduleConfig]

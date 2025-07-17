from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from db.database import get_db
from db.crud import (
    get_task, get_tasks_by_user, update_task, delete_task,
    create_task_schedule_config, get_task_schedule_config, get_task_schedule_configs,
    count_task_schedule_configs, update_task_schedule_config, delete_task_schedule_config
)
from models.user import User
from schemas.task import Task, TaskCreate, TaskUpdate
from schemas.task import TaskScheduleConfig, TaskScheduleConfigCreate, TaskScheduleConfigUpdate, TaskScheduleConfigList
from schemas.response import ResponseBase, create_success_response, create_error_response, ErrorType
from utils.auth_utils import get_current_active_user

router = APIRouter()


@router.get("", response_model=List[Task], summary="获取当前用户的任务列表")
def read_tasks(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前用户的任务列表
    """
    tasks = get_tasks_by_user(db, current_user.id, skip=skip, limit=limit)
    return tasks


@router.get("/{task_id}", response_model=Task, summary="获取任务详情")
def read_task(
    task_id: int = Path(..., description="任务ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取指定任务的详情
    """
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 检查任务是否属于当前用户
    if task.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="没有权限访问该任务")
    
    return task


@router.get("/status/{task_id}", response_model=ResponseBase, summary="获取任务状态")
def read_task_status(
    task_id: int = Path(..., description="任务ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取指定任务的状态信息
    """
    task = get_task(db, task_id)
    if not task:
                return create_error_response(
            message="任务不存在",
                    error_type=ErrorType.NOT_FOUND,
            code=status.HTTP_404_NOT_FOUND
        )
    
    # 检查任务是否属于当前用户
    if task.user_id != current_user.id and not current_user.is_superuser:
        return create_error_response(
            message="没有权限访问该任务",
            error_type=ErrorType.PERMISSION_DENIED,
            code=status.HTTP_403_FORBIDDEN
        )
    
    # 解析任务结果
    result = None
    if task.result:
        try:
            import json
            result = json.loads(task.result)
        except:
            result = task.result
    
    # 解析任务参数
    params = None
    if task.params:
        try:
            if isinstance(task.params, str):
                params = json.loads(task.params)
            else:
                params = task.params
        except:
            params = task.params
    
    return create_success_response(
        message="获取任务状态成功",
        data={
            "id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "progress": task.progress,
            "params": params,
            "result": result,
            "error": task.error,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None
        }
    )


@router.delete("/{task_id}", response_model=ResponseBase, summary="取消/删除任务")
def delete_task_endpoint(
    task_id: int = Path(..., description="任务ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    取消或删除指定任务
    """
    task = get_task(db, task_id)
    if not task:
                return create_error_response(
            message="任务不存在",
                    error_type=ErrorType.NOT_FOUND,
            code=status.HTTP_404_NOT_FOUND
        )
    
    # 检查任务是否属于当前用户
    if task.user_id != current_user.id and not current_user.is_superuser:
        return create_error_response(
            message="没有权限删除该任务",
            error_type=ErrorType.PERMISSION_DENIED,
            code=status.HTTP_403_FORBIDDEN
        )
    
    # 删除任务
    delete_task(db, task_id)
    
    return create_success_response(
        message="任务已成功删除",
        data={"id": task_id}
    )


# 任务调度配置相关接口
@router.post("/schedule", response_model=TaskScheduleConfig, summary="创建任务调度配置", status_code=status.HTTP_201_CREATED)
def create_schedule_config(
    config: TaskScheduleConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    创建新的任务调度配置
    
    - **name**: 配置名称（唯一）
    - **description**: 配置描述
    - **task_type**: 任务类型
    - **schedule_type**: 调度类型(crontab或interval)
    - **minute**: 分钟 (crontab格式)
    - **hour**: 小时 (crontab格式)
    - **day_of_week**: 星期几 (crontab格式)
    - **day_of_month**: 日期 (crontab格式)
    - **month_of_year**: 月份 (crontab格式)
    - **interval_seconds**: 间隔秒数 (interval格式)
    - **start_time**: 开始时间 (HH:MM:SS)
    - **end_time**: 结束时间 (HH:MM:SS)
    - **enabled**: 是否启用
    """
    # 检查权限（只有超级管理员可以创建调度配置）
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以创建任务调度配置"
        )
    
    # 检查名称是否已存在
    existing_config = db.query(TaskScheduleConfig).filter(TaskScheduleConfig.name == config.name).first()
    if existing_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"配置名称 '{config.name}' 已存在"
        )
    
    # 创建配置
    return create_task_schedule_config(db, config)


@router.get("/schedule", response_model=TaskScheduleConfigList, summary="获取任务调度配置列表")
def read_schedule_configs(
    skip: int = Query(0, description="跳过的记录数"),
    limit: int = Query(100, description="返回的最大记录数"),
    task_type: Optional[str] = Query(None, description="任务类型过滤"),
    enabled: Optional[bool] = Query(None, description="是否启用过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取任务调度配置列表
    """
    # 检查权限（只有超级管理员可以查看所有调度配置）
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以查看任务调度配置"
        )
    
    configs = get_task_schedule_configs(db, skip, limit, task_type, enabled)
    total = count_task_schedule_configs(db, task_type, enabled)
    
    return {
        "total": total,
        "items": configs
    }


@router.get("/schedule/{config_id}", response_model=TaskScheduleConfig, summary="获取任务调度配置详情")
def read_schedule_config(
    config_id: int = Path(..., description="配置ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取指定任务调度配置的详情
    """
    # 检查权限（只有超级管理员可以查看调度配置）
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以查看任务调度配置"
        )
    
    config = get_task_schedule_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务调度配置不存在"
        )
    
    return config


@router.put("/schedule/{config_id}", response_model=TaskScheduleConfig, summary="更新任务调度配置")
def update_schedule_config(
    config_id: int,
    config_update: TaskScheduleConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    更新指定任务调度配置
    """
    # 检查权限（只有超级管理员可以更新调度配置）
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以更新任务调度配置"
        )
    
    # 检查配置是否存在
    existing_config = get_task_schedule_config(db, config_id)
    if not existing_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务调度配置不存在"
        )
    
    # 如果更新了名称，检查新名称是否已存在
    if config_update.name and config_update.name != existing_config.name:
        name_exists = db.query(TaskScheduleConfig).filter(
            TaskScheduleConfig.name == config_update.name,
            TaskScheduleConfig.id != config_id
        ).first()
        if name_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"配置名称 '{config_update.name}' 已存在"
            )
    
    # 更新配置
    updated_config = update_task_schedule_config(db, config_id, config_update)
    if not updated_config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新任务调度配置失败"
        )
    
    return updated_config


@router.delete("/schedule/{config_id}", response_model=ResponseBase, summary="删除任务调度配置")
def delete_schedule_config(
    config_id: int = Path(..., description="配置ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    删除指定任务调度配置
    """
    # 检查权限（只有超级管理员可以删除调度配置）
    if not current_user.is_superuser:
        return create_error_response(
            message="只有管理员可以删除任务调度配置",
            error_type=ErrorType.PERMISSION_DENIED,
            code=status.HTTP_403_FORBIDDEN
        )
    
    # 检查配置是否存在
    config = get_task_schedule_config(db, config_id)
    if not config:
            return create_error_response(
            message="任务调度配置不存在",
            error_type=ErrorType.NOT_FOUND,
            code=status.HTTP_404_NOT_FOUND
        )
    
    # 删除配置
    success = delete_task_schedule_config(db, config_id)
    if not success:
        return create_error_response(
            message="删除任务调度配置失败",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return create_success_response(
        message="任务调度配置已成功删除",
        data={"id": config_id}
        )

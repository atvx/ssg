from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict

from db.database import get_db
from db.crud import get_tasks_by_user, get_task, delete_task
from schemas.task import Task, TaskStatus
from schemas.user import User
from schemas.response import APIResponse, StatusCode, ErrorType
from utils.security import get_current_active_user

router = APIRouter()


@router.get("")
def read_tasks(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户的任务列表"""
    tasks = get_tasks_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return create_success_response(
        message="获取任务列表成功",
        data=tasks
    )


@router.get("/{task_id}")
def read_task(
    task_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取指定任务详情"""
    db_task = get_task(db, task_id=task_id)
    if db_task is None or db_task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail={
                "msg": "任务不存在或无权限访问",
                "field": "task_id"
            }
        )
    return create_success_response(
        message="获取任务详情成功",
        data=db_task
    )


@router.get("/status/{task_id}")
def get_task_status(
    task_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取任务状态"""
    task = get_task(db, task_id=task_id)
    if task is None or task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail={
                "msg": "任务不存在或无权限访问",
                "field": "task_id"
            }
        )
    
    # 构建任务状态
    task_status = TaskStatus(
        task_id=task.id,
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        result=task.result
    )
    
    return create_success_response(
        message="获取任务状态成功",
        data=task_status
    )


@router.delete("/{task_id}")
def remove_task(
    task_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除任务"""
    db_task = get_task(db, task_id=task_id)
    if db_task is None or db_task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail={
                "msg": "任务不存在或无权限访问",
                "field": "task_id"
            }
        )
    
    try:
        deleted_task = delete_task(db, task_id=task_id)
        return create_success_response(
            message="任务删除成功",
            data=deleted_task
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "msg": str(e),
                "field": "task_id"
            }
        )

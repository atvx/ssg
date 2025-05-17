from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.db.crud import get_task, get_tasks_by_user, update_task
from app.schemas.task import Task, TaskStatus
from app.utils.security import get_current_active_user
from app.schemas.user import User

router = APIRouter()


@router.get("", response_model=List[Task])
def get_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户的任务列表"""
    return get_tasks_by_user(db, current_user.id, skip, limit)


@router.get("/{task_id}", response_model=Task)
def get_task_detail(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取任务详情"""
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 验证任务是否属于当前用户
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return task


@router.get("/status/{task_id}", response_model=TaskStatus)
def get_task_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取任务状态"""
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 验证任务是否属于当前用户
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return TaskStatus(
        id=task.id,
        status=task.status,
        progress=task.progress
    )


@router.delete("/{task_id}", response_model=Task)
def cancel_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """取消任务"""
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 验证任务是否属于当前用户
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # 只有处于pending或running状态的任务可以取消
    if task.status not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel task in {task.status} status")
    
    # 更新任务状态
    from app.schemas.task import TaskUpdate
    updated_task = update_task(db, task_id, TaskUpdate(status="cancelled"))
    
    # TODO: 实际中还需要调用Celery的revoke来停止正在运行的任务
    
    return updated_task

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict

from db.database import get_db
from db.crud import get_tasks_by_user, get_task, delete_task
from schemas.task import Task, TaskStatus
from schemas.user import User
from schemas.response import APIResponse, StatusCode, ErrorType
from utils.security import get_current_active_user
from utils.response_utils import create_success_response, create_error_response

router = APIRouter()


@router.get("", summary="获取当前用户的任务列表")
def read_tasks(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前用户的任务列表
    
    参数:
    - skip: 跳过记录数，默认0
    - limit: 返回记录数上限，默认100
    """
    tasks = get_tasks_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return create_success_response(
        message="获取任务列表成功",
        data=tasks
    )


@router.get("/{task_id}", summary="获取任务详情")
def read_task(
    task_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取任务详情
    
    参数:
    - task_id: 任务ID
    """
    try:
        try:
            db_task = get_task(db, task_id=task_id)
            if db_task is None or db_task.user_id != current_user.id:
                return create_error_response(
                    message="任务不存在或无权限访问",
                    error_type=ErrorType.NOT_FOUND,
                    code=status.HTTP_404_NOT_FOUND,
                    details=[{
                        "field": "task_id",
                        "message": "任务不存在或无权限访问"
                    }]
                )
            return create_success_response(
                message="获取任务详情成功",
                data=db_task
            )
        except ValueError as e:
            return create_error_response(
                message=str(e),
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "task_id",
                    "message": str(e)
                }]
            )
            
    except Exception as e:
        return create_error_response(
            message=f"获取任务详情失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.get("/status/{task_id}", summary="获取任务状态")
def get_task_status(
    task_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取任务状态
    
    参数:
    - task_id: 任务ID
    """
    try:
        try:
            task = get_task(db, task_id=task_id)
            if task is None or task.user_id != current_user.id:
                return create_error_response(
                    message="任务不存在或无权限访问",
                    error_type=ErrorType.NOT_FOUND,
                    code=status.HTTP_404_NOT_FOUND,
                    details=[{
                        "field": "task_id",
                        "message": "任务不存在或无权限访问"
                    }]
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
        except ValueError as e:
            return create_error_response(
                message=str(e),
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "task_id",
                    "message": str(e)
                }]
            )
            
    except Exception as e:
        return create_error_response(
            message=f"获取任务状态失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.delete("/{task_id}", summary="删除任务")
def remove_task(
    task_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    删除任务
    
    参数:
    - task_id: 任务ID
    """
    try:
        try:
            db_task = get_task(db, task_id=task_id)
            if db_task is None or db_task.user_id != current_user.id:
                return create_error_response(
                    message="任务不存在或无权限访问",
                    error_type=ErrorType.NOT_FOUND,
                    code=status.HTTP_404_NOT_FOUND,
                    details=[{
                        "field": "task_id",
                        "message": "任务不存在或无权限访问"
                    }]
                )
            
            deleted_task = delete_task(db, task_id=task_id)
            return create_success_response(
                message="任务删除成功",
                data=deleted_task
            )
        except ValueError as e:
            return create_error_response(
                message=str(e),
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "task_id",
                    "message": str(e)
                }]
            )
            
    except Exception as e:
        return create_error_response(
            message=f"删除任务失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )

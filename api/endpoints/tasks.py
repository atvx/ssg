from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import json
import logging

from db.database import get_db
from db.crud import get_tasks_by_user, get_task, delete_task
from schemas.task import Task, TaskStatus
from schemas.user import User
from schemas.response import APIResponse, StatusCode, ErrorType
from utils.security import get_current_active_user
from utils.response_utils import create_success_response, create_error_response
from celery_app.tasks import fetch_meituan_task, fetch_duowei_task, fetch_all_data_task

router = APIRouter()

logger = logging.getLogger(__name__)


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


@router.post("/execute/{task_id}", summary="直接执行任务")
def execute_task(
    task_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    直接执行任务（重新提交到Celery队列）
    
    参数:
    - task_id: 任务ID
    
    返回:
    - 执行结果信息
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
            
            # 根据任务类型选择相应的Celery任务
            # 从任务记录中获取信息以重新执行
            date = None  # 实际项目中需从记录或参数中获取日期
            user_id = task.user_id
            
            # 从任务参数中获取查询日期
            if task.params:
                try:
                    task_params = json.loads(task.params)
                    date = task_params.get("date")
                    logger.info(f"[任务ID: {task_id}] 从任务参数中获取查询日期: {date}")
                except json.JSONDecodeError:
                    logger.warning(f"[任务ID: {task_id}] 任务参数解析失败: {task.params}")
            
            if task.task_type == "fetch_meituan":
                # 执行美团数据获取任务
                result = fetch_meituan_task.apply_async(args=[task_id, date, user_id], task_id=f"{task_id}")
                task_name = "美团数据"
            elif task.task_type == "fetch_duowei":
                # 执行多维数据获取任务
                result = fetch_duowei_task.apply_async(args=[task_id, date, user_id], task_id=f"{task_id}")
                task_name = "多维数据"
            elif task.task_type == "fetch_all":
                # 执行全平台数据获取任务
                result = fetch_all_data_task.apply_async(args=[task_id, date, user_id], task_id=f"{task_id}")
                task_name = "全平台数据"
            else:
                return create_error_response(
                    message=f"不支持的任务类型: {task.task_type}",
                    error_type=ErrorType.VALIDATION_ERROR,
                    code=status.HTTP_400_BAD_REQUEST
                )
            
            return create_success_response(
                message=f"已重新执行{task_name}获取任务",
                data={
                    "task_id": task_id,
                    "celery_task_id": result.id if hasattr(result, 'id') else None,
                    "status": "submitted",
                    "status_check_url": f"/api/tasks/status/{task_id}"
                }
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
            message=f"执行任务失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )

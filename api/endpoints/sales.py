from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import logging

from db.database import get_db
from db.crud import create_task, get_warehouses
from services.data_service import get_merged_data, get_all_platforms, get_all_warehouses
from schemas.sales import SalesRecord, FetchDataRequest, WarehouseInfo
from schemas.task import TaskCreate, Task
from celery_app.tasks import fetch_meituan_task, fetch_duowei_task, fetch_all_data_task
from utils.security import get_current_active_user
from schemas.user import User
from schemas.response import APIResponse, StatusCode, ErrorType
from services.sales_service import get_all_sales_data, get_sales_data_by_date
from utils.response_utils import create_success_response, create_error_response

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/fetch", summary="数据同步任务")
def fetch_data_get(
    date: Optional[str] = None,
    platform: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    数据同步任务
    
    参数:
    - date: 查询日期（格式 YYYY-MM-DD），为空时默认为当前日期
    - platform: 指定获取数据的平台，不指定则获取所有平台数据，可选
    
    返回:
    - 创建的数据同步任务信息
    """
    try:
        try:
            # 处理日期参数
            today = datetime.now().date()
            
            # 解析date，如果提供
            query_date = None
            if date:
                try:
                    query_date = datetime.strptime(date, "%Y-%m-%d").date()
                    logger.info(f"GET请求: 收到日期参数 {date} -> 解析为 {query_date}")
                except ValueError:
                    return create_error_response(
                        message="无效的日期格式，应为YYYY-MM-DD",
                        error_type=ErrorType.VALIDATION_ERROR,
                        code=status.HTTP_400_BAD_REQUEST,
                        details=[{
                            "field": "date",
                            "message": "无效的日期格式，应为YYYY-MM-DD"
                        }]
                    )
            else:
                # 未提供日期参数，使用当前日期
                query_date = today
                logger.info(f"GET请求: 未提供日期参数，使用当前日期 {query_date}")
            
            # 转换为字符串格式
            date_str = query_date.isoformat()
            
            logger.info(f"GET请求: 获取数据，查询日期: {date_str}")
            
            # 平台验证
            valid_platforms = set(["meituan", "duowei"])
            
            if platform and platform not in valid_platforms:
                return create_error_response(
                    message=f"不支持的平台: {platform}",
                    error_type=ErrorType.VALIDATION_ERROR,
                    code=status.HTTP_400_BAD_REQUEST,
                    details=[{
                        "field": "platform",
                        "message": f"不支持的平台: {platform}，有效选项: {list(valid_platforms)}"
                    }]
                )
            
            # 根据请求的平台创建不同类型的任务
            task = None
            if not platform:
                # 获取所有平台数据
                task = create_task(db, TaskCreate(task_type="fetch_all"), current_user.id)
                fetch_all_data_task.delay(task.id, date_str)
            elif platform == "meituan":
                # 只获取美团数据
                task = create_task(db, TaskCreate(task_type="fetch_meituan"), current_user.id)
                fetch_meituan_task.delay(task.id, date_str)
            elif platform == "duowei":
                # 只获取多维数据
                task = create_task(db, TaskCreate(task_type="fetch_duowei"), current_user.id)
                fetch_duowei_task.delay(task.id, date_str)
            
            return create_success_response(
                message=f"已启动{platform if platform else '全平台'}数据同步任务",
                data={
                    "task_id": task.id,
                    "status": task.status,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "date": date_str
                }
            )
        except ValueError as e:
            return create_error_response(
                message=str(e),
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "date" if "日期" in str(e) else 
                            "platform" if "平台" in str(e) else
                            "request_params",
                    "message": str(e)
                }]
            )
            
    except Exception as e:
        logger.error(f"启动数据同步任务失败: {str(e)}")
        return create_error_response(
            message=f"启动数据同步任务失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )

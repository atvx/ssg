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


@router.get("/all", summary="获取所有销售数据")
def get_all_sales(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    platform: Optional[str] = None,
    warehouse: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取所有销售数据
    
    可选参数:
    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    - platform: 平台筛选
    - warehouse: 仓库筛选
    """
    try:
        sales_data = get_all_sales_data(
            db, 
            start_date=start_date,
            end_date=end_date,
            platform=platform,
            warehouse=warehouse
        )
        
        # 转换为前端需要的格式
        response_data = []
        for platform_name, platform_data in sales_data.items():
            platform_obj = {
                "platform": platform_name,
                "total_sales": sum(day_data["sales"] for day_data in platform_data),
                "total_orders": sum(day_data["orders"] for day_data in platform_data),
                "days": platform_data
            }
            response_data.append(platform_obj)
        
        return create_success_response(
            message="销售数据获取成功",
            data=response_data
        )
    
    except Exception as e:
        logger.error(f"获取销售数据失败: {str(e)}")
        return create_error_response(
            message=f"获取销售数据失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.get("/by-date/{date_str}", summary="获取指定日期的销售数据")
def get_sales_by_date(
    date_str: str,
    platform: Optional[str] = None,
    warehouse: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取指定日期的销售数据
    
    参数:
    - date_str: 日期字符串 (YYYY-MM-DD)
    
    可选参数:
    - platform: 平台筛选
    - warehouse: 仓库筛选
    """
    try:
        # 验证日期格式
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "msg": "日期格式无效，请使用YYYY-MM-DD格式",
                    "field": "date"
                }
            )
        
        sales_data = get_sales_data_by_date(
            db, 
            target_date,
            platform=platform,
            warehouse=warehouse
        )
        
        return create_success_response(
            message=f"{date_str}销售数据获取成功",
            data=sales_data
        )
    
    except HTTPException:
        # 直接重新抛出HTTP异常，让全局处理器处理
        raise
    
    except Exception as e:
        logger.error(f"获取销售数据失败: {str(e)}")
        return create_error_response(
            message=f"获取销售数据失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.get("/fetch", summary="数据同步任务")
def fetch_data_get(
    date: Optional[str] = None,
    platform: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    触发获取销售数据的后台任务(GET方法)
    
    - date: 查询日期（格式 YYYY-MM-DD），为空时默认为当前日期
    - platform: 可选，指定获取数据的平台，不指定则获取所有平台数据
    """
    # 处理日期参数
    today = datetime.now().date()
    
    # 解析date，如果提供
    query_date = None
    if date:
        try:
            query_date = datetime.strptime(date, "%Y-%m-%d").date()
            logger.info(f"GET请求: 收到日期参数 {date} -> 解析为 {query_date}")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "msg": "无效的日期格式，应为YYYY-MM-DD",
                    "field": "date"
                }
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "msg": f"不支持的平台: {platform}",
                "field": "platform",
                "valid_options": list(valid_platforms)
            }
        )
    
    try:
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
            message="数据获取任务已创建",
            data=task
        )
    except Exception as e:
        logger.error(f"创建数据获取任务失败: {str(e)}")
        return create_error_response(
            message="创建数据获取任务失败",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.get("/platforms", summary="获取支持的数据平台列表")
def get_platforms(
    current_user: User = Depends(get_current_active_user)
):
    """获取支持的数据平台列表"""
    platforms = get_all_platforms()
    return create_success_response(
        message="获取平台列表成功",
        data=platforms
    )


@router.get("/warehouses", summary="获取所有仓库列表")
def get_all_warehouse_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取所有仓库列表"""
    try:
        warehouses = get_all_warehouses(db)
        return create_success_response(
            message="获取仓库列表成功",
            data=warehouses
        )
    except Exception as e:
        logger.error(f"获取仓库列表失败: {str(e)}")
        return create_error_response(
            message="获取仓库列表失败",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.get("/warehouses/{platform}", summary="获取指定平台的仓库列表")
def get_warehouse_list_by_platform(
    platform: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取指定平台的仓库列表"""
    valid_platforms = set(get_all_platforms())
    if platform not in valid_platforms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "msg": f"不支持的平台: {platform}",
                "field": "platform",
                "valid_options": list(valid_platforms)
            }
        )
    
    try:
        warehouses = get_all_warehouses(db, platform)
        return create_success_response(
            message=f"获取{platform}平台仓库列表成功",
            data=warehouses
        )
    except Exception as e:
        logger.error(f"获取仓库列表失败: {str(e)}")
        return create_error_response(
            message="获取仓库列表失败",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.get("/task/fetch-data", summary="手动获取销售数据")
def fetch_sales_data(
    days: Optional[int] = Query(7, description="要获取多少天的数据"),
    platform: Optional[str] = Query(None, description="平台筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # 计算日期，默认为当前日期
    date_str = datetime.now().date().isoformat()
    
    # 平台验证
    valid_platforms = set(["meituan", "duowei"])
    
    if platform and platform not in valid_platforms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "msg": f"不支持的平台: {platform}",
                "field": "platform",
                "valid_options": list(valid_platforms)
            }
        )
    
    try:
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
            message="数据获取任务已创建",
            data=task
        )
    except Exception as e:
        logger.error(f"创建数据获取任务失败: {str(e)}")
        return create_error_response(
            message="创建数据获取任务失败",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.get("/meituan", summary="手动获取美团销售数据")
def get_meituan_data(
    date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> APIResponse:
    """
    同步获取美团销售数据
    
    此接口会直接运行数据爬取而不是创建一个后台任务
    
    Args:
        date: 查询日期（格式为YYYY-MM-DD），为空时默认为当天
        
    Returns:
        APIResponse: 数据获取结果，包含仓库销售数据和汇总信息
    """
    try:
        # 使用重构后的服务
        from services.meituan_service import get_all_meituan_data
        
        result = get_all_meituan_data(db, date)
        
        # 检查是否获取成功
        if not result["success"]:
            return create_error_response(
                message=result["message"],
                error_type=ErrorType.SERVER_ERROR,
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # 成功返回
        return create_success_response(
            message="美团数据获取成功",
            data={
                "summary": result.get("summary", {}),
                "data": result.get("data", []),
                "date": result.get("date", ""),
                "platform": result.get("platform", "meituan")
            }
        )
    except Exception as e:
        logger.error(f"获取美团数据失败: {e}")
        return create_error_response(
            message=f"获取美团数据失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

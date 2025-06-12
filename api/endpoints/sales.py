from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status, Path
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import logging

from db.database import get_db
from db.crud import (
    create_task, get_warehouses, 
    create_monthly_sales_target, get_sales_targets,
    get_monthly_sales_target, update_monthly_sales_target, delete_monthly_sales_target
)
from services.data_service import get_merged_data, get_all_platforms, get_all_warehouses
from schemas.sales import (
    SalesRecord, FetchDataRequest, WarehouseInfo,
    MonthlySalesTarget, MonthlySalesTargetCreate, MonthlySalesTargetUpdate,
    MonthlySalesTargetResponse, MonthlySalesTargetListResponse
)
from schemas.task import TaskCreate, Task
from celery_app.tasks import fetch_meituan_task, fetch_duowei_task, fetch_all_data_task
from utils.security import get_current_active_user, get_current_superuser
from schemas.user import User
from schemas.response import APIResponse, StatusCode, ErrorType
from services.sales_service import get_all_sales_data, get_sales_data_by_date
from services.meituan_service import fetch_meituan_data
from services.duowei_service import fetch_duowei_data
from utils.response_utils import create_success_response, create_error_response

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/fetch", summary="数据同步任务（支持同步/异步模式）")
def fetch_data_get(
    date: Optional[str] = None,
    platform: Optional[str] = None,
    user_id: Optional[int] = None,
    sync: bool = Query(False, description="是否同步执行（true=同步返回结果，false=异步执行返回任务信息）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    数据同步任务（支持同步/异步两种执行模式）
    
    参数:
    - date: 查询日期（格式 YYYY-MM-DD），为空时默认为当前日期
    - platform: 指定获取数据的平台，不指定则获取所有平台数据，可选
    - user_id: 指定用户ID，可选
    - sync: 执行模式（true=同步执行立即返回结果，false=异步执行返回任务信息），默认false
    
    返回:
    - sync=true: 直接返回数据结果
    - sync=false: 返回任务信息，需要通过任务状态API查询结果
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
            
            # 根据执行模式选择同步或异步执行
            if sync:
                # 同步执行模式 - 直接调用服务函数并返回结果
                logger.info(f"同步模式: 开始获取{platform if platform else '全平台'}数据")
                
                if not platform:
                    # 获取所有平台数据
                    meituan_result = fetch_meituan_data(db, date_str, user_id)
                    duowei_result = fetch_duowei_data(date_str, db)
                    
                    # 合并结果
                    all_data = {
                        "success": meituan_result.get("success", False) or duowei_result.get("success", False),
                        "message": "数据获取完成",
                        "date": date_str,
                        "execution_mode": "sync",
                        "platforms": {
                            "meituan": {
                                "success": meituan_result.get("success", False),
                                "message": meituan_result.get("message", ""),
                                "data": meituan_result.get("data", [])
                            },
                            "duowei": {
                                "success": duowei_result.get("success", False),
                                "message": duowei_result.get("message", ""),
                                "data": duowei_result.get("data", [])
                            }
                        }
                    }
                    
                    return create_success_response(
                        message="全平台数据获取完成",
                        data=all_data
                    )
                    
                elif platform == "meituan":
                    # 只获取美团数据
                    result = fetch_meituan_data(db, date_str, user_id)
                    result["execution_mode"] = "sync"
                    
                    if result.get("success", False):
                        return create_success_response(
                            message="美团数据获取成功",
                            data=result
                        )
                    else:
                        return create_error_response(
                            message=f"美团数据获取失败: {result.get('message', '未知错误')}",
                            error_type=ErrorType.SERVER_ERROR,
                            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            details=[{
                                "field": "meituan_service",
                                "message": result.get("message", "未知错误")
                            }]
                        )
                        
                elif platform == "duowei":
                    # 只获取多维数据
                    result = fetch_duowei_data(date_str, db)
                    result["execution_mode"] = "sync"
                    
                    if result.get("success", False):
                        return create_success_response(
                            message="多维数据获取成功",
                            data=result
                        )
                    else:
                        return create_error_response(
                            message=f"多维数据获取失败: {result.get('message', '未知错误')}",
                            error_type=ErrorType.SERVER_ERROR,
                            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            details=[{
                                "field": "duowei_service",
                                "message": result.get("message", "未知错误")
                            }]
                        )
            else:
                # 异步执行模式 - 使用Celery任务队列
                logger.info(f"异步模式: 创建{platform if platform else '全平台'}数据同步任务")
                
            task = None
            if not platform:
                # 获取所有平台数据
                task = create_task(db, TaskCreate(task_type="fetch_all"), current_user.id)
                fetch_all_data_task.delay(task.id, date_str, user_id)
            elif platform == "meituan":
                # 只获取美团数据
                task = create_task(db, TaskCreate(task_type="fetch_meituan"), current_user.id)
                fetch_meituan_task.delay(task.id, date_str, user_id)
            elif platform == "duowei":
                # 只获取多维数据
                task = create_task(db, TaskCreate(task_type="fetch_duowei"), current_user.id)
                fetch_duowei_task.delay(task.id, date_str, user_id)
            
            return create_success_response(
                message=f"已启动{platform if platform else '全平台'}数据同步任务",
                data={
                    "task_id": task.id,
                    "status": task.status,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "date": date_str,
                        "user_id": user_id,
                        "execution_mode": "async",
                        "status_check_url": f"/api/tasks/status/{task.id}"
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

# 月度销售目标相关接口
@router.post("/targets", response_model=MonthlySalesTargetResponse, status_code=status.HTTP_201_CREATED, summary="新增销售目标")
def create_sales_target(
    target: MonthlySalesTargetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    新增月度销售目标
    
    参数:
    - org_id: 组织ID
    - year: 年份
    - month: 月份
    - target_income: 目标收入
    - sort: 排序值，可选
    
    返回:
    - 创建成功的销售目标信息
    """
    try:
        try:
            existing_targets = get_sales_targets(
                db, 
                org_id=target.org_id, 
                year=target.year, 
                month=target.month
            )
            
            if existing_targets:
                return create_error_response(
                    message=f"该组织({target.org_id})在{target.year}年{target.month}月已存在销售目标",
                    error_type=ErrorType.VALIDATION_ERROR,
                    code=status.HTTP_400_BAD_REQUEST,
                    details=[{
                        "field": "org_id",
                        "message": "组织在指定月份已存在销售目标"
                    }]
                )
            
            # 创建新目标
            new_target = create_monthly_sales_target(db, target)
            
            return create_success_response(
                code=StatusCode.CREATED,
                message="销售目标创建成功",
                data=new_target
            )
        except ValueError as e:
            return create_error_response(
                message=str(e),
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "request_body",
                    "message": str(e)
                }]
            )
            
    except Exception as e:
        logger.error(f"创建销售目标失败: {str(e)}")
        return create_error_response(
            message=f"创建销售目标失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.get("/targets", response_model=MonthlySalesTargetListResponse, summary="获取销售目标列表")
def list_sales_targets(
    skip: int = 0,
    limit: int = 100,
    org_id: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取月度销售目标列表，支持筛选
    
    参数:
    - skip: 跳过记录数，默认0
    - limit: 返回记录数上限，默认100
    - org_id: 组织ID筛选，可选
    - year: 年份筛选，可选
    - month: 月份筛选，可选
    
    返回:
    - 销售目标列表
    """
    try:
        targets = get_sales_targets(
            db,
            skip=skip,
            limit=limit,
            org_id=org_id,
            year=year,
            month=month
        )
        
        return create_success_response(
            message="获取销售目标列表成功",
            data=targets
        )
    except Exception as e:
        logger.error(f"获取销售目标列表失败: {str(e)}")
        return create_error_response(
            message=f"获取销售目标列表失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.get("/targets/{target_id}", response_model=MonthlySalesTargetResponse, summary="获取销售目标详情")
def get_sales_target(
    target_id: int = Path(..., description="销售目标ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取单个销售目标详情
    
    参数:
    - target_id: 销售目标ID
    
    返回:
    - 销售目标详情
    """
    try:
        target = get_monthly_sales_target(db, target_id)
        
        if not target:
            return create_error_response(
                message=f"ID为{target_id}的销售目标不存在",
                error_type=ErrorType.NOT_FOUND,
                code=status.HTTP_404_NOT_FOUND,
                details=[{
                    "field": "target_id",
                    "message": "销售目标不存在"
                }]
            )
            
        return create_success_response(
            message="获取销售目标详情成功",
            data=target
        )
    except Exception as e:
        logger.error(f"获取销售目标详情失败: {str(e)}")
        return create_error_response(
            message=f"获取销售目标详情失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.put("/targets/{target_id}", response_model=MonthlySalesTargetResponse, summary="更新销售目标")
def update_sales_target(
    target_id: int = Path(..., description="销售目标ID"),
    target_update: MonthlySalesTargetUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    更新销售目标信息
    
    参数:
    - target_id: 销售目标ID
    - org_id: 组织ID，可选
    - year: 年份，可选
    - month: 月份，可选
    - target_income: 目标收入，可选
    - sort: 排序值，可选
    
    返回:
    - 更新后的销售目标信息
    """
    try:
        try:
            # 检查目标是否存在
            existing_target = get_monthly_sales_target(db, target_id)
            
            if not existing_target:
                return create_error_response(
                    message=f"ID为{target_id}的销售目标不存在",
                    error_type=ErrorType.NOT_FOUND,
                    code=status.HTTP_404_NOT_FOUND,
                    details=[{
                        "field": "target_id",
                        "message": "销售目标不存在"
                    }]
                )
            
            # 如果修改了组织/年/月，检查是否与其他记录冲突
            if (target_update.org_id or target_update.year or target_update.month) and \
                (target_update.org_id != existing_target.org_id or 
                target_update.year != existing_target.year or 
                target_update.month != existing_target.month):
                
                org_id = target_update.org_id or existing_target.org_id
                year = target_update.year or existing_target.year
                month = target_update.month or existing_target.month
                
                conflicting_targets = get_sales_targets(
                    db, org_id=org_id, year=year, month=month
                )
                
                if any(t.id != target_id for t in conflicting_targets):
                    return create_error_response(
                        message=f"该组织({org_id})在{year}年{month}月已存在销售目标",
                        error_type=ErrorType.VALIDATION_ERROR,
                        code=status.HTTP_400_BAD_REQUEST,
                        details=[{
                            "field": "org_id",
                            "message": "组织在指定月份已存在销售目标"
                        }]
                    )
            
            # 更新目标
            updated_target = update_monthly_sales_target(db, target_id, target_update)
            
            return create_success_response(
                message="销售目标更新成功",
                data=updated_target
            )
        except ValueError as e:
            return create_error_response(
                message=str(e),
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "request_body",
                    "message": str(e)
                }]
            )
            
    except Exception as e:
        logger.error(f"更新销售目标失败: {str(e)}")
        return create_error_response(
            message=f"更新销售目标失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.delete("/targets/{target_id}", summary="删除销售目标")
def delete_sales_target(
    target_id: int = Path(..., description="销售目标ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    删除销售目标
    
    参数:
    - target_id: 销售目标ID
    
    返回:
    - 删除操作结果
    """
    try:
        # 检查目标是否存在
        existing_target = get_monthly_sales_target(db, target_id)
        
        if not existing_target:
            return create_error_response(
                message=f"ID为{target_id}的销售目标不存在",
                error_type=ErrorType.NOT_FOUND,
                code=status.HTTP_404_NOT_FOUND,
                details=[{
                    "field": "target_id",
                    "message": "销售目标不存在"
                }]
            )
        
        # 删除目标
        success = delete_monthly_sales_target(db, target_id)
        
        if success:
            return create_success_response(
                message="销售目标删除成功"
            )
        else:
            return create_error_response(
                message="销售目标删除失败",
                error_type=ErrorType.SERVER_ERROR,
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    except Exception as e:
        logger.error(f"删除销售目标失败: {str(e)}")
        return create_error_response(
            message=f"删除销售目标失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )

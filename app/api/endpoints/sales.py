from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime

from app.db.database import get_db
from app.db.crud import create_task, get_warehouses
from app.services.data_service import get_merged_data, get_all_platforms, get_all_warehouses
from app.schemas.sales import SalesRecord, FetchDataRequest, WarehouseInfo
from app.schemas.task import TaskCreate, Task
from app.celery_app.tasks import fetch_meituan_task, fetch_duowei_task, fetch_all_data_task
from app.utils.security import get_current_active_user
from app.schemas.user import User

router = APIRouter()


@router.get("", response_model=List[SalesRecord])
def get_all_sales(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    platform: Optional[str] = None,
    warehouse_name: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取所有销售数据，支持按日期、平台和仓库筛选"""
    sales_data = get_merged_data(
        db, 
        start_date=start_date, 
        end_date=end_date, 
        platform=platform, 
        warehouse_name=warehouse_name
    )
    return sales_data[skip:skip+limit]


@router.get("/{date_str}", response_model=List[SalesRecord])
def get_sales_by_date(
    date_str: str,
    platform: Optional[str] = None,
    warehouse_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取指定日期的销售数据"""
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    sales_data = get_merged_data(
        db, 
        start_date=target_date, 
        end_date=target_date, 
        platform=platform, 
        warehouse_name=warehouse_name
    )
    return sales_data


@router.post("/fetch", response_model=Task)
def fetch_data(
    request: FetchDataRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """触发获取销售数据的后台任务"""
    date_str = request.date.isoformat() if request.date else None
    
    # 根据请求的平台创建不同类型的任务
    if not request.platforms or len(request.platforms) == 0 or set(request.platforms) == {"meituan", "duowei"}:
        # 获取所有平台数据
        task = create_task(db, TaskCreate(task_type="fetch_all"), current_user.id)
        fetch_all_data_task.delay(task.id, date_str)
    elif "meituan" in request.platforms:
        # 只获取美团数据
        task = create_task(db, TaskCreate(task_type="fetch_meituan"), current_user.id)
        fetch_meituan_task.delay(task.id, date_str)
    elif "duowei" in request.platforms:
        # 只获取多维数据
        task = create_task(db, TaskCreate(task_type="fetch_duowei"), current_user.id)
        fetch_duowei_task.delay(task.id, date_str)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {request.platforms}")
    
    return task


@router.get("/platforms", response_model=List[str])
def get_platforms(
    current_user: User = Depends(get_current_active_user)
):
    """获取支持的数据平台列表"""
    return get_all_platforms()


@router.get("/warehouses", response_model=List[WarehouseInfo])
def get_all_warehouse_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取所有仓库列表"""
    return get_all_warehouses(db)


@router.get("/warehouses/{platform}", response_model=List[WarehouseInfo])
def get_warehouse_list_by_platform(
    platform: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取指定平台的仓库列表"""
    if platform not in get_all_platforms():
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    
    return get_all_warehouses(db, platform)

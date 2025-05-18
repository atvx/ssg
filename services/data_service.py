from typing import List, Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from db.crud import get_sales_records, get_warehouses
from services.meituan_service import fetch_meituan_data
from services.duowei_service import fetch_duowei_data


def get_merged_data(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    platform: Optional[str] = None,
    warehouse_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    获取数据库中的合并销售数据
    
    Args:
        db: 数据库会话
        start_date: 开始日期
        end_date: 结束日期
        platform: 平台 ("meituan" 或 "duowei")
        warehouse_name: 仓库名称
    
    Returns:
        List[Dict]: 销售数据列表
    
    Raises:
        HTTPException: 当查询数据库失败时
    """
    try:
        # 验证平台参数
        if platform and platform not in get_all_platforms():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"msg": f"不支持的平台: {platform}", "field": "platform", "valid_options": get_all_platforms()}
            )
        
        # 从数据库获取数据
        records = get_sales_records(
            db, 
            start_date=start_date,
            end_date=end_date, 
            platform=platform,
            warehouse_name=warehouse_name
        )
        
        # 转换为API响应格式
        result = []
        for record in records:
            result.append({
                "id": record.id,
                "date": record.date.isoformat(),
                "platform": record.platform,
                "name": record.warehouse_name,
                "incomeAmt": float(record.income_amt),
                "salesCartCount": record.sales_cart_count,
                "avgIncomeAmt": float(record.avg_income_amt),
                "createdAt": record.created_at.isoformat()
            })
        
        return result
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"msg": "数据库查询失败", "error_type": "database_error"}
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"msg": "获取销售数据失败", "error_type": "data_service_error"}
        )


def get_all_platforms() -> List[str]:
    """获取支持的所有平台列表"""
    return ["meituan", "duowei"]


def get_all_warehouses(db: Session, platform: Optional[str] = None) -> List[Dict[str, str]]:
    """
    获取所有仓库列表
    
    Args:
        db: 数据库会话
        platform: 可选的平台筛选
    
    Returns:
        List[Dict]: 仓库列表，每个元素包含name和platform字段
    
    Raises:
        HTTPException: 当查询仓库列表失败时
    """
    try:
        # 验证平台参数
        if platform and platform not in get_all_platforms():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"msg": f"不支持的平台: {platform}", "field": "platform", "valid_options": get_all_platforms()}
            )
            
        return get_warehouses(db, platform)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"msg": "数据库查询仓库失败", "error_type": "database_error"}
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"msg": "获取仓库列表失败", "error_type": "warehouse_service_error"}
        )

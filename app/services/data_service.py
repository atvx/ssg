from typing import List, Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session

from app.db.crud import get_sales_records, get_warehouses
from app.services.meituan_service import fetch_meituan_data
from app.services.duowei_service import fetch_duowei_data


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
    """
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
    """
    return get_warehouses(db, platform)

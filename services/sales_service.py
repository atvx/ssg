from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
import logging

from models.sales import SalesRecord as DBSalesRecord

logger = logging.getLogger(__name__)

def get_all_sales_data(
    db: Session,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    platform: Optional[str] = None,
    warehouse: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    获取所有销售数据，按平台分组
    
    参数:
        db: 数据库会话
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        platform: 平台名称
        warehouse: 仓库名称
        
    返回:
        按平台分组的销售数据
    """
    # 构建查询
    query = db.query(DBSalesRecord)
    
    # 应用筛选条件
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(DBSalesRecord.date >= start_date_obj)
        except ValueError:
            logger.warning(f"无效的开始日期格式: {start_date}")
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(DBSalesRecord.date <= end_date_obj)
        except ValueError:
            logger.warning(f"无效的结束日期格式: {end_date}")
    
    if platform:
        query = query.filter(DBSalesRecord.platform == platform)
    
    if warehouse:
        query = query.filter(DBSalesRecord.warehouse_name == warehouse)
    
    # 获取所有记录
    sales_records = query.all()
    
    # 按平台和日期整理数据
    result = {}
    for record in sales_records:
        platform_name = record.platform
        date_str = record.date.isoformat()
        
        if platform_name not in result:
            result[platform_name] = []
        
        # 查找该平台下是否已有该日期的数据
        day_data = None
        for day in result[platform_name]:
            if day["date"] == date_str:
                day_data = day
                break
        
        # 如果没有找到该日期的数据，创建一个新的
        if not day_data:
            day_data = {
                "date": date_str,
                "sales": 0,
                "orders": 0,
                "warehouses": []
            }
            result[platform_name].append(day_data)
        
        # 更新统计数据
        day_data["sales"] += float(record.income_amt)
        day_data["orders"] += record.sales_cart_count
        
        # 添加仓库数据
        warehouse_data = {
            "name": record.warehouse_name,
            "sales": float(record.income_amt),
            "orders": record.sales_cart_count
        }
        day_data["warehouses"].append(warehouse_data)
    
    # 按日期排序
    for platform_name in result:
        result[platform_name].sort(key=lambda x: x["date"])
    
    return result


def get_sales_data_by_date(
    db: Session,
    target_date: date,
    platform: Optional[str] = None,
    warehouse: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    获取指定日期的销售数据
    
    参数:
        db: 数据库会话
        target_date: 目标日期
        platform: 平台名称
        warehouse: 仓库名称
        
    返回:
        指定日期的销售数据列表
    """
    # 构建查询
    query = db.query(DBSalesRecord).filter(DBSalesRecord.date == target_date)
    
    # 应用筛选条件
    if platform:
        query = query.filter(DBSalesRecord.platform == platform)
    
    if warehouse:
        query = query.filter(DBSalesRecord.warehouse_name == warehouse)
    
    # 获取所有记录
    sales_records = query.all()
    
    # 按平台整理数据
    result = []
    platforms = {}
    
    for record in sales_records:
        platform_name = record.platform
        
        if platform_name not in platforms:
            platforms[platform_name] = {
                "platform": platform_name,
                "date": target_date.isoformat(),
                "total_sales": 0,
                "total_orders": 0,
                "warehouses": []
            }
            result.append(platforms[platform_name])
        
        # 更新平台统计数据
        platforms[platform_name]["total_sales"] += float(record.income_amt)
        platforms[platform_name]["total_orders"] += record.sales_cart_count
        
        # 添加仓库数据
        warehouse_data = {
            "name": record.warehouse_name,
            "sales": float(record.income_amt),
            "orders": record.sales_cart_count
        }
        platforms[platform_name]["warehouses"].append(warehouse_data)
    
    return result 
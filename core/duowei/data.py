import json
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

from utils.data_utils import decimal_default


def calculate_sales_stats(sales_data):
    """
    计算销售统计数据，使用Decimal确保金额精度
    
    Args:
        sales_data: 销售数据列表
        
    Returns:
        dict: 包含总销售额、销售数量和平均销售额的字典
    """
    # 初始化统计变量
    total_jezj = Decimal('0.00')
    total_zk = Decimal('0.00')
    total_dtsjyye = Decimal('0.00')
    valid_store_count = 0
    
    # 处理每个门店数据（统计有效门店）
    for store in sales_data:
        jezj = Decimal(str(store.get('jezj', 0)))
        zk = Decimal(str(store.get('zk', 0)))
        dtsjyye = Decimal(str(store.get('dtsjyye', 0)))
        
        # 计算有效门店数量（jezj不为0且不为空的门店）
        if jezj != 0 and jezj is not None:
            # 累加总计值
            total_jezj += jezj
            total_zk += zk
            total_dtsjyye += dtsjyye
            valid_store_count += 1
    
    # 计算结果数据
    total_sales_amount = total_jezj.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    valid_car_count = valid_store_count
    
    # 计算平均值，避免除零错误
    if valid_car_count > 0:
        avg_sales_amount = (total_sales_amount / Decimal(valid_car_count)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        avg_sales_amount = Decimal('0.00')
    
    return {
        "incomeAmt": float(total_sales_amount),
        "salesCartCount": valid_car_count,
        "avgIncomeAmt": float(avg_sales_amount)
    }


def get_all_duowei_data(config, date=None):
    """
    获取所有仓库的销售数据
    
    Args:
        config: 配置字典
        date: 查询日期，格式为YYYY-MM-DD，默认为当天
    
    Returns:
        list: 所有仓库的销售数据
    """
    from .api import get_warehouse_info, get_sales_data
    
    # 当前查询日期
    query_date = date if date else datetime.now().strftime("%Y-%m-%d")
    print(f"查询日期: {query_date}")
    
    # 获取仓库信息
    warehouses = get_warehouse_info(config)
    
    # 存储所有仓库销售结果
    all_warehouse_sales = []
    
    # 为每个仓库获取销售数据
    for warehouse in warehouses:
        warehouse_name = warehouse.get("name")
        children = warehouse.get("children", [])
        
        # 组合门店编号字符串，格式为 @SSG003@@SSG004@...
        child_ids = [child.get("id") for child in children if child.get("id")]
        bmbh_string = "@" + "@".join(child_ids) + "@" if child_ids else ""
        
        if bmbh_string:
            # 获取销售数据
            sales_data = get_sales_data(config, bmbh_string, query_date)
            
            # 计算销售统计
            if sales_data:
                sales_stats = calculate_sales_stats(sales_data)
                
                # 添加仓库名称
                sales_stats["name"] = warehouse_name
                
                # 添加到结果列表
                all_warehouse_sales.append(sales_stats)
            else:
                # 如果没有销售数据，添加空统计
                all_warehouse_sales.append({
                    "name": warehouse_name,
                    "incomeAmt": 0,
                    "salesCartCount": 0,
                    "avgIncomeAmt": 0
                })
    
    return all_warehouse_sales 
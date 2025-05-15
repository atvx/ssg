import requests
import json
import re
import time
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

def get_warehouse_info():
    """
    从API获取仓库信息，包含仓库及其下属车辆
    """
    # 接口地址
    url = "http://saas.wxdw.top:8899/web_api/jgsz"

    # 请求参数
    params = {
        "yhbh": "00016",
        "db_name": "ssgmlj",
    }

    # 发送 GET 请求
    response = requests.get(url, params=params)

    # 解析响应内容
    if response.status_code == 200:
        try:
            data = response.json()
            if data["status"] == 1 and "data" in data:
                all_stores = data["data"]
                
                # 步骤1: 从数据中筛选出名称包含"仓"的门店
                warehouse_stores = []
                warehouse_bmbhs = []
                for store in all_stores:
                    if "bmmc" in store and re.search(r"仓", store["bmmc"]):
                        warehouse_stores.append(store)
                        if "bmbh" in store:
                            warehouse_bmbhs.append(store["bmbh"])
                
                # 步骤2: 找到这些仓库的所有子门店
                child_stores_by_parent = {}
                for warehouse_bmbh in warehouse_bmbhs:
                    child_stores_by_parent[warehouse_bmbh] = []
                    
                for store in all_stores:
                    if "fbmbh" in store and store["fbmbh"] in warehouse_bmbhs:
                        parent_bmbh = store["fbmbh"]
                        child_stores_by_parent[parent_bmbh].append(store)
                
                # 步骤3: 构建仓库信息结构
                result = []
                for warehouse in warehouse_stores:
                    warehouse_bmbh = warehouse.get("bmbh", "")
                    warehouse_json = {
                        "id": warehouse.get("bmbh", ""),
                        "name": warehouse.get("bmmc", ""),
                        "pid": warehouse.get("fbmbh", ""),
                        "children": []
                    }
                    
                    # 添加子门店
                    if warehouse_bmbh in child_stores_by_parent:
                        children = child_stores_by_parent[warehouse_bmbh]
                        for child in children:
                            child_json = {
                                "id": child.get("bmbh", ""),
                                "name": child.get("bmmc", ""),
                                "pid": child.get("fbmbh", "")
                            }
                            warehouse_json["children"].append(child_json)
                    
                    result.append(warehouse_json)
                
                return result
            else:
                print("API返回错误或数据结构不符合预期")
                return []
        except json.JSONDecodeError:
            print("返回内容不是有效的JSON格式")
            return []
    else:
        print("请求失败")
        return []

def get_sales_data(bmbh_string, date=None):
    """
    获取销售数据
    
    Args:
        bmbh_string: 门店编号字符串
        date: 日期字符串，格式为YYYY-MM-DD，默认为当天
    """
    # 如果未指定日期，使用当天日期
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # 接口地址
    url = "http://saas.wxdw.top:8899/web_api/mdyyzshz"

    # 请求参数
    params = {
        "begindt": date,
        "enddt": date,
        "bmbh": bmbh_string,
        "db_name": "ssgmlj"
    }

    # 发送 GET 请求
    response = requests.get(url, params=params)

    # 解析响应内容
    if response.status_code == 200:
        result = response.json()
        if result.get('status') == 1 and result.get('msg') == 'ok':
            return result.get('data', [])
        else:
            print(f"请求返回错误: {result.get('msg')}")
            return []
    else:
        print(f"请求失败，状态码: {response.status_code}")
        print(response.text)
        return []

def calculate_sales_stats(sales_data):
    """
    计算销售统计数据，使用Decimal确保金额精度
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

def decimal_default(obj):
    """
    处理Decimal类型的JSON序列化
    """
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError("Object of type '%s' is not JSON serializable" % type(obj).__name__)

def main(date=None):
    """
    主函数
    
    Args:
        date: 查询日期，格式为YYYY-MM-DD，默认为当天
    """
    # 获取仓库信息
    warehouses = get_warehouse_info()
    
    # 当前查询日期
    query_date = date if date else datetime.now().strftime("%Y-%m-%d")
    print(f"查询日期: {query_date}")
    
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
            sales_data = get_sales_data(bmbh_string, query_date)
            
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
    
    # 输出结果
    print(json.dumps(all_warehouse_sales, ensure_ascii=False, indent=2, default=decimal_default))
    return all_warehouse_sales

if __name__ == "__main__":
    import sys
    
    # 如果命令行提供日期参数，则使用提供的日期，否则使用当天日期
    if len(sys.argv) > 1:
        date_arg = sys.argv[1]
        main(date_arg)
    else:
        main()

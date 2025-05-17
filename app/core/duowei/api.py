import requests
import json
import re


def get_warehouse_info(config):
    """
    从API获取仓库信息，包含仓库及其下属车辆
    
    Args:
        config: 配置字典
        
    Returns:
        list: 仓库信息列表
    """
    # 接口地址
    url = f"{config['BASE_URL']}/jgsz"

    # 请求参数
    params = {
        "yhbh": config["USER_ID"],
        "db_name": config["DB_NAME"],
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


def get_sales_data(config, bmbh_string, date=None):
    """
    获取销售数据
    
    Args:
        config: 配置字典
        bmbh_string: 门店编号字符串
        date: 日期字符串，格式为YYYY-MM-DD，默认为当天
    """
    # 接口地址
    url = f"{config['BASE_URL']}/mdyyzshz"

    # 请求参数
    params = {
        "begindt": date,
        "enddt": date,
        "bmbh": bmbh_string,
        "db_name": config["DB_NAME"]
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
        return [] 
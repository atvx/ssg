warehouses = [
    {"sort": 1, "name": "重庆江北仓"},
    {"sort": 2, "name": "重庆渝北仓"},
    {"sort": 3, "name": "重庆二郎仓"},
    {"sort": 4, "name": "重庆大学城仓"},
    {"sort": 5, "name": "重庆北碚仓"},
    {"sort": 6, "name": "重庆南岸仓"},
    {"sort": 7, "name": "重庆中央公园仓"},
    {"sort": 8, "name": "重庆北部新区仓"},
    {"sort": 11, "name": "昆明龙泉仓"},
    {"sort": 12, "name": "昆明广卫仓"},
    {"sort": 13, "name": "昆明世博仓"}
]

import json
import pandas as pd

# 读取两个JSON文件并合并数据
with open('sales_duowei.json', 'r', encoding='utf-8') as f:
    sales_duowei = json.load(f)

with open('sales_meituan.json', 'r', encoding='utf-8') as f:
    sales_meituan = json.load(f)

# 合并两个文件的数据
sales_data = sales_duowei + sales_meituan

# 创建一个字典，用于快速查找销售数据
sales_dict = {item['name']: item for item in sales_data}

# 创建结果列表
result = []

# 根据warehouses列表，整合数据
for warehouse in warehouses:
    name = warehouse['name']
    sort = warehouse['sort']
    
    # 如果在sales_data中找到相应的仓库数据，则添加到结果中
    if name in sales_dict:
        data = sales_dict[name]
        result.append({
            '名称': name,
            '车辆配置': data.get('salesCartCount', ''),
            '当日销售': data.get('incomeAmt', ''),
            '当日车均': data.get('avgIncomeAmt', '')
        })
    else:
        # 如果没有找到销售数据，添加空值
        result.append({
            '名称': name,
            '车辆配置': '',
            '当日销售': '',
            '当日车均': ''
        })

# 转换为DataFrame
df = pd.DataFrame(result)

# 添加一个临时的排序列，然后排序
warehouse_sort_dict = {warehouse['name']: warehouse['sort'] for warehouse in warehouses}
df['sort'] = df['名称'].map(warehouse_sort_dict)
df = df.sort_values('sort').drop('sort', axis=1)

# 保存为Excel文件
df.to_excel('仓库销售数据.xlsx', index=False)

print('Excel文件已生成：仓库销售数据.xlsx')



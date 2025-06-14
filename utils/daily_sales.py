import os
import pandas as pd
import pymysql
from sqlalchemy import create_engine
from datetime import datetime
from dotenv import load_dotenv
import sys
from pathlib import Path
import json
from excel import export_json_to_excel
from decimal import Decimal, ROUND_HALF_UP

# 获取项目根目录
root_dir = Path(__file__).parent.parent
# 加载.env文件
load_dotenv(os.path.join(root_dir, '.env'))

def get_connection():
    """连接到数据库"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("错误：未找到DATABASE_URL环境变量")
            sys.exit(1)
        
        engine = create_engine(database_url)
        return engine
    except Exception as e:
        print(f"连接数据库时出错: {str(e)}")
        sys.exit(1)

def format_percentage(value):
    """将小数格式化为百分比字符串"""
    return f"{value:.1f}%" if pd.notna(value) else "0.0%"

def calculate_summary(warehouses_data):
    """计算仓库列表的汇总数据"""
    if not warehouses_data:
        return {}
    
    # 累加基础数据
    summary = {
        'car_count': 0,           # 1.车辆配置：累加值
        'daily_revenue': 0,       # 2.当日销售：累加值
        'daily_cart_count': 0,    # 4.当日车次：累加值
        'target_income': 0,       # 5.月目标：累加值
        'actual_income': 0,       # 6.月累计：累加值
        'sold_car_count': 0       # 9.累计车次：累加值
    }
    
    # 累加所有基础数据
    for warehouse in warehouses_data:
        summary['car_count'] += warehouse.get('car_count', 0)
        summary['daily_revenue'] += warehouse.get('daily_revenue', 0)
        summary['daily_cart_count'] += warehouse.get('daily_cart_count', 0)
        summary['target_income'] += warehouse.get('target_income', 0)
        summary['actual_income'] += warehouse.get('actual_income', 0)
        summary['sold_car_count'] += warehouse.get('sold_car_count', 0)
    
    # 3.当日车均 = 当日销售 / 当日车次
    if summary['daily_cart_count'] > 0:
        # 使用Decimal进行精确计算和四舍五入
        daily_revenue = Decimal(str(summary['daily_revenue']))
        daily_cart_count = Decimal(str(summary['daily_cart_count']))
        daily_avg = daily_revenue / daily_cart_count
        # 四舍五入到整数
        summary['daily_avg_revenue_cart'] = int(daily_avg.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    else:
        summary['daily_avg_revenue_cart'] = 0
    
    # 7.累计达成率 = 月累计 / 月目标
    if summary['target_income'] > 0:
        # 使用Decimal进行精确计算
        actual_income = Decimal(str(summary['actual_income']))
        target_income = Decimal(str(summary['target_income']))
        ach_rate = (actual_income / target_income) * Decimal('100')
        summary['ach_rate'] = format_percentage(ach_rate)
    else:
        summary['ach_rate'] = "0.0%"
    
    # 8.累计车均 = 月累计 / 累计车次
    if summary['sold_car_count'] > 0:
        # 使用Decimal进行精确计算和四舍五入
        actual_income = Decimal(str(summary['actual_income']))
        sold_car_count = Decimal(str(summary['sold_car_count']))
        per_car = actual_income / sold_car_count
        # 四舍五入到整数
        summary['per_car_income'] = int(per_car.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    else:
        summary['per_car_income'] = 0
    
    return summary

def process_data_to_json(df):
    """处理DataFrame为所需的JSON格式"""
    if df.empty:
        return {"markets": [], "total": {}}
    
    # 获取当前日期作为报表日期
    now = datetime.now()
    report_date = now.strftime('%Y-%m-%d')
    
    # 确保数值列是数值类型
    numeric_columns = ['car_count', 'daily_revenue', 'daily_avg_revenue_cart', 'daily_cart_count',
                       'target_income', 'actual_income', 'per_car_income', 'sold_car_count']
    
    for col in numeric_columns:
        if col in df.columns:
            # 使用round函数四舍五入后再转换为int，避免截断问题
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).round().astype(int)
    
    # 格式化ach_rate为百分比字符串
    df['ach_rate_str'] = df['ach_rate'].apply(lambda x: format_percentage(x))
    
    # 按parent_name分组，但保留排序信息
    result = {"markets": []}
    all_warehouses = []
    
    # 创建市场数据字典，按p_sort排序
    market_dict = {}
    for _, row in df.iterrows():
        parent_name = row['parent_name']
        p_sort = row['p_sort']
        if parent_name not in market_dict:
            market_dict[parent_name] = {
                'name': parent_name,
                'sort': p_sort,
                'rows': []
            }
        market_dict[parent_name]['rows'].append(row)
    
    # 按p_sort排序市场
    sorted_markets = sorted(market_dict.values(), key=lambda x: x['sort'])
    
    # 处理每个市场的数据，添加id字段
    for market_idx, market_info in enumerate(sorted_markets, 1):
        parent_name = market_info['name']
        market_data = {
            "id": market_idx,  # 添加市场id字段
            "name": parent_name,
            "warehouses": []
        }
        
        # 按c_sort排序仓库
        sorted_rows = sorted(market_info['rows'], key=lambda x: x['c_sort'])
        
        # 处理每个仓库的数据
        for idx, row in enumerate(sorted_rows, 1):
            warehouse = {
                "id": idx,  # 在每个市场内的顺序ID
                "name": row['name'],
                "car_count": round(row['car_count']) if pd.notna(row['car_count']) else 0,
                "daily_revenue": round(row['daily_revenue']) if pd.notna(row['daily_revenue']) else 0,
                "daily_avg_revenue_cart": round(row['daily_avg_revenue_cart']) if pd.notna(row['daily_avg_revenue_cart']) else 0,
                "daily_cart_count": round(row['daily_cart_count']) if pd.notna(row['daily_cart_count']) else 0,
                "target_income": round(row['target_income']) if pd.notna(row['target_income']) else 0,
                "actual_income": round(row['actual_income']) if pd.notna(row['actual_income']) else 0,
                "ach_rate": row['ach_rate_str'],
                "per_car_income": round(row['per_car_income']) if pd.notna(row['per_car_income']) else 0,
                "sold_car_count": round(row['sold_car_count']) if pd.notna(row['sold_car_count']) else 0
            }
            
            market_data["warehouses"].append(warehouse)
            all_warehouses.append(warehouse)
        
        # 计算市场汇总数据
        market_data["summary"] = calculate_summary(market_data["warehouses"])
        
        result["markets"].append(market_data)
    
    # 计算总体汇总数据
    result["total"] = calculate_summary(all_warehouses)
    
    # 添加报表日期
    result["report_date"] = report_date
    
    return result

def execute_query():
    """执行每日销售查询"""
    # 获取当前日期
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    query_date = '2025-06-12'
    
    # 构建SQL查询
    query = f"""
    SELECT 
     c.id,
     c.name,
     t.car_count,
     ROUND(s.income_amt, 0) AS daily_revenue,
     ROUND(s.avg_income_amt, 0) AS daily_avg_revenue_cart,
     s.sales_cart_count AS daily_cart_count,
     ROUND(t.target_income, 0) AS target_income,
     ROUND(t.actual_income, 0) AS actual_income,
     t.ach_rate,
     ROUND(t.per_car_income, 0) AS per_car_income,
     t.sold_car_count,
     p.id AS parent_id,
     p.name AS parent_name,
     p.sort AS p_sort,
     c.sort AS c_sort
    FROM orgs AS c
    LEFT JOIN orgs AS p ON p.id = c.parent_id
    LEFT JOIN sales_records s ON s.warehouse_name = c.name
    LEFT JOIN sales_target t ON t.org_name = s.warehouse_name AND t.year = {current_year} AND t.month = {current_month}
    WHERE c.org_type = 3 AND s.date = '{query_date}'
    ORDER BY p.sort ASC, c.sort ASC
    """
    
    try:
        # 连接数据库
        engine = get_connection()
        
        # 执行查询
        print(f"正在查询 {query_date} 的销售数据...")
        print(f"年份: {current_year}, 月份: {current_month}")
        
        # 使用pandas读取查询结果
        df = pd.read_sql(query, engine)
        
        # 检查结果
        if df.empty:
            print("查询结果为空，没有找到当日销售数据")
            return
        
        # 处理数据为JSON格式
        result_json = process_data_to_json(df)
        
        # 打印JSON结果
        print("\n处理后的销售数据JSON:")
        print(json.dumps(result_json, indent=4, ensure_ascii=False))
        
        # 保存JSON到文件
        output_file = os.path.join(root_dir, 'data', 'daily_sales.json')
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_json, f, indent=4, ensure_ascii=False)
        
        print(f"\nJSON数据已保存至: {output_file}")
        
        # 导出Excel文件
        excel_filename = os.path.join(root_dir, 'data', f"市场销售数据_{query_date}.xlsx")
        export_json_to_excel(result_json, query_date, excel_filename)
        print(f"Excel文件已导出至: {excel_filename}")
        
    except Exception as e:
        print(f"执行查询或处理数据时出错: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    execute_query()

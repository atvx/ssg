import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
import logging

from db.crud import get_daily_sales_data
from utils.file_format_utils import (
    set_excel_landscape_format, 
    convert_xlsx_to_pdf, 
    convert_pdf_to_png, 
    ensure_directory_exists
)
from utils.excel import export_json_to_excel

logger = logging.getLogger(__name__)


class DailyReportService:
    """日报业务服务类"""
    
    def __init__(self, data_dir: str = None):
        """
        初始化日报服务
        
        Args:
            data_dir: 数据文件存储目录，默认为项目根目录下的data文件夹
        """
        if data_dir is None:
            # 获取项目根目录
            current_file = Path(__file__)
            project_root = current_file.parent.parent  # 从services目录往上两级
            self.data_dir = project_root / 'data'
        else:
            self.data_dir = Path(data_dir)
        
        # 确保数据目录存在
        ensure_directory_exists(str(self.data_dir))
    
    def format_percentage(self, value: Any) -> str:
        """
        将数值格式化为百分比字符串
        
        Args:
            value: 数值
            
        Returns:
            str: 百分比字符串
        """
        if pd.notna(value) and value is not None:
            try:
                return f"{float(value):.1f}%"
            except (ValueError, TypeError):
                return "0.0%"
        return "0.0%"
    
    def calculate_summary(self, warehouses_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算仓库列表的汇总数据
        
        Args:
            warehouses_data: 仓库数据列表
            
        Returns:
            Dict: 汇总数据
        """
        if not warehouses_data:
            return {}
        
        # 累加基础数据
        summary = {
            'car_count': 0,  # 1.车辆配置：累加值
            'daily_revenue': 0,  # 2.当日销售：累加值
            'daily_cart_count': 0,  # 4.当日车次：累加值
            'target_income': 0,  # 5.月目标：累加值
            'actual_income': 0,  # 6.月累计：累加值
            'sold_car_count': 0  # 9.累计车次：累加值
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
            summary['ach_rate'] = self.format_percentage(ach_rate)
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
    
    def process_raw_data_to_report_format(self, raw_data: List[Dict[str, Any]], report_date: str = None) -> Dict[str, Any]:
        """
        处理原始数据为日报JSON格式
        
        Args:
            raw_data: 原始数据列表
            report_date: 报表日期，默认为当前日期
            
        Returns:
            Dict: 日报数据
        """
        if not raw_data:
            return {"markets": [], "total": {}}
        
        # 获取报表日期
        if report_date is None:
            report_date = datetime.now().strftime('%Y-%m-%d')
        
        # 转换为DataFrame便于处理
        df = pd.DataFrame(raw_data)
        
        # 确保数值列是数值类型
        numeric_columns = ['car_count', 'daily_revenue', 'daily_avg_revenue_cart', 'daily_cart_count',
                          'target_income', 'actual_income', 'per_car_income', 'sold_car_count']
        
        for col in numeric_columns:
            if col in df.columns:
                # 使用round函数四舍五入后再转换为int，避免截断问题
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).round().astype(int)
        
        # 格式化ach_rate为百分比字符串
        df['ach_rate_str'] = df['ach_rate'].apply(lambda x: self.format_percentage(x))
        
        # 按parent_name分组，但保留排序信息
        result = {"markets": []}
        all_warehouses = []
        
        # 创建市场数据字典，按p_sort排序
        market_dict = {}
        for _, row in df.iterrows():
            parent_name = row['parent_name']
            p_sort = row.get('p_sort', 0)
            if parent_name not in market_dict:
                market_dict[parent_name] = {
                    'name': parent_name,
                    'sort': p_sort,
                    'rows': []
                }
            market_dict[parent_name]['rows'].append(row)
        
        # 按p_sort排序市场
        sorted_markets = sorted(market_dict.values(), key=lambda x: x.get('sort', 0))
        
        # 处理每个市场的数据，添加id字段
        for market_idx, market_info in enumerate(sorted_markets, 1):
            parent_name = market_info['name']
            market_data = {
                "id": market_idx,  # 添加市场id字段
                "name": parent_name,
                "warehouses": []
            }
            
            # 按c_sort排序仓库
            sorted_rows = sorted(market_info['rows'], key=lambda x: x.get('c_sort', 0))
            
            # 处理每个仓库的数据
            for idx, row in enumerate(sorted_rows, 1):
                warehouse = {
                    "id": idx,  # 在每个市场内的顺序ID
                    "name": row['name'],
                    "car_count": int(row.get('car_count', 0)) if pd.notna(row.get('car_count')) else 0,
                    "daily_revenue": int(row.get('daily_revenue', 0)) if pd.notna(row.get('daily_revenue')) else 0,
                    "daily_avg_revenue_cart": int(row.get('daily_avg_revenue_cart', 0)) if pd.notna(row.get('daily_avg_revenue_cart')) else 0,
                    "daily_cart_count": int(row.get('daily_cart_count', 0)) if pd.notna(row.get('daily_cart_count')) else 0,
                    "target_income": int(row.get('target_income', 0)) if pd.notna(row.get('target_income')) else 0,
                    "actual_income": int(row.get('actual_income', 0)) if pd.notna(row.get('actual_income')) else 0,
                    "ach_rate": row.get('ach_rate_str', '0.0%'),
                    "per_car_income": int(row.get('per_car_income', 0)) if pd.notna(row.get('per_car_income')) else 0,
                    "sold_car_count": int(row.get('sold_car_count', 0)) if pd.notna(row.get('sold_car_count')) else 0
                }
                
                market_data["warehouses"].append(warehouse)
                all_warehouses.append(warehouse)
            
            # 计算市场汇总数据
            market_data["summary"] = self.calculate_summary(market_data["warehouses"])
            
            result["markets"].append(market_data)
        
        # 计算总体汇总数据
        result["total"] = self.calculate_summary(all_warehouses)
        
        # 添加报表日期
        result["report_date"] = report_date
        
        return result
    
    def export_daily_report(
        self, 
        db: Session,
        query_date: str = None, 
        export_formats: List[str] = None
    ) -> Dict[str, Any]:
        """
        导出日报
        
        Args:
            db: 数据库会话
            query_date: 查询日期，格式YYYY-MM-DD，默认为当前日期
            export_formats: 导出格式列表，可选值：['excel', 'pdf', 'png']，默认全部导出
            
        Returns:
            Dict: 导出结果，包含成功状态、消息、数据和文件路径
        """
        try:
            # 处理默认参数
            if query_date is None:
                query_date = datetime.now().strftime('%Y-%m-%d')
            
            if export_formats is None:
                export_formats = ['excel', 'pdf', 'png']
            
            # 验证日期格式
            try:
                datetime.strptime(query_date, '%Y-%m-%d')
            except ValueError:
                raise ValueError("无效的日期格式，应为YYYY-MM-DD")
            
            logger.info(f"开始导出日报: 查询日期={query_date}, 导出格式={export_formats}")
            
            # 从数据库获取原始数据
            raw_data = get_daily_sales_data(db, query_date)
            
            # 检查数据是否存在
            if not raw_data:
                return {
                    "success": False,
                    "message": "查询结果为空，没有找到当日销售数据",
                    "data": None,
                    "files": {}
                }
            
            # 处理数据为JSON格式
            report_data = self.process_raw_data_to_report_format(raw_data, query_date)
            
            # 存储文件路径
            files = {}
            
            # 导出Excel文件
            if 'excel' in export_formats:
                excel_file = self.data_dir / f"市场销售数据_{query_date}.xlsx"
                export_json_to_excel(report_data, query_date, str(excel_file))
                files['excel'] = str(excel_file)
                logger.info(f"✓ Excel文件已导出至: {excel_file}")
                
                # 设置Excel为横向打印格式
                set_excel_landscape_format(str(excel_file), sheetname="市场日报")
            
            # 转换Excel为PDF
            if 'pdf' in export_formats and 'excel' in files:
                xlsx_path = Path(files['excel'])
                pdf_path = convert_xlsx_to_pdf(xlsx_path)
                files['pdf'] = str(pdf_path)
                logger.info(f"✓ PDF文件已生成: {pdf_path}")
            
            # 转换PDF为PNG
            if 'png' in export_formats and 'pdf' in files:
                pdf_path = Path(files['pdf'])
                png_path = convert_pdf_to_png(pdf_path)
                files['png'] = str(png_path)
                logger.info(f"✓ PNG图片已生成: {png_path}")
            
            return {
                "success": True,
                "message": f"日报导出成功（{query_date}）",
                "data": report_data,
                "files": files,
                "export_formats": export_formats,
                "query_date": query_date
            }
            
        except Exception as e:
            logger.error(f"导出日报时出错: {str(e)}")
            return {
                "success": False,
                "message": f"导出日报失败: {str(e)}",
                "data": None,
                "files": {},
                "error": str(e)
            } 
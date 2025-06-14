import logging
from datetime import datetime, date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class SalesTargetService:
    """销售目标服务类"""
    
    @staticmethod
    def update_monthly_targets(db: Session, query_date: Optional[str] = None) -> dict:
        """
        更新月度销售目标数据
        
        Args:
            db: 数据库会话
            query_date: 查询日期，格式YYYY-MM-DD，默认为当前日期
            
        Returns:
            dict: 更新结果，包含成功状态、消息和更新行数
        """
        try:
            # 处理日期参数
            if query_date:
                # 如果提供了日期字符串，解析它
                if isinstance(query_date, str):
                    date_obj = datetime.strptime(query_date, '%Y-%m-%d').date()
                else:
                    date_obj = query_date
            else:
                # 使用当前日期
                date_obj = datetime.now().date()
            
            # 从日期中提取年份和月份
            target_year = date_obj.year
            target_month = date_obj.month
            
            logger.info(f"开始更新{target_year}年{target_month}月的销售目标数据")
            
            # 构建动态SQL
            update_sql = text("""
                UPDATE sales_target AS st
                JOIN (
                    SELECT
                        t.org_name,
                        IFNULL(s.total_income_amt, 0) AS actual_income,
                        IFNULL(s.total_sales_cart_count, 0) AS sold_car_count,
                        ROUND(IFNULL(s.total_income_amt, 0) / NULLIF(IFNULL(s.total_sales_cart_count, 0), 0), 2) AS per_car_income,
                        ROUND(IFNULL(s.total_income_amt, 0) / NULLIF(IFNULL(t.target_income, 0), 0) * 100, 1) AS ach_rate 
                    FROM orgs AS c
                    LEFT JOIN (
                        SELECT
                            warehouse_name,
                            SUM(income_amt) AS total_income_amt,
                            SUM(sales_cart_count) AS total_sales_cart_count 
                        FROM sales_records 
                        WHERE YEAR(DATE) = :target_year AND MONTH(DATE) = :target_month 
                        GROUP BY warehouse_name 
                    ) AS s ON c.name = s.warehouse_name
                    LEFT JOIN (
                        SELECT org_name, target_income, car_count FROM sales_target WHERE YEAR = :target_year AND MONTH = :target_month 
                    ) AS t ON c.name = t.org_name 
                    WHERE c.org_type = 3 
                ) AS upd ON st.org_name = upd.org_name 
                AND st.YEAR = :target_year 
                AND st.MONTH = :target_month 
                SET st.actual_income = upd.actual_income,
                st.sold_car_count = upd.sold_car_count,
                st.per_car_income = upd.per_car_income,
                st.ach_rate = upd.ach_rate,
                st.updated_at = NOW()
            """)
            
            # 执行SQL更新
            result = db.execute(update_sql, {
                "target_year": target_year,
                "target_month": target_month
            })
            db.commit()
            
            # 获取更新的行数
            updated_rows = result.rowcount
            logger.info(f"成功更新了{updated_rows}条销售目标记录")
            
            return {
                "success": True,
                "message": f"成功更新了{updated_rows}条销售目标记录",
                "updated_rows": updated_rows,
                "year": target_year,
                "month": target_month
            }
            
        except Exception as e:
            logger.error(f"更新月目标失败: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "message": f"更新月目标失败: {str(e)}",
                "updated_rows": 0,
                "error": str(e)
            } 
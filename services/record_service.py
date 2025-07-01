from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, text
from typing import List, Optional, Dict, Any
from datetime import date as date_type
import logging
import math
from decimal import Decimal, ROUND_HALF_UP

from models.sales import SalesRecord
from schemas.record import (
    SalesRecordCreate, SalesRecordUpdate, SalesRecordQuery,
    SalesRecordListData, PageInfo, SalesRecordSummary, SalesRecordResponse
)

logger = logging.getLogger(__name__)


class RecordService:
    """销售记录服务类"""
    
    @staticmethod
    def get_sales_record(db: Session, record_id: int) -> Optional[SalesRecord]:
        """
        根据记录ID获取销售记录
        
        Args:
            db: 数据库会话
            record_id: 记录ID
            
        Returns:
            Optional[SalesRecord]: 销售记录，不存在则返回None
        """
        try:
            return db.query(SalesRecord).filter(SalesRecord.id == record_id).first()
        except SQLAlchemyError as e:
            logger.error(f"查询销售记录出错: {str(e)}")
            raise
    
    @staticmethod
    def get_sales_records(db: Session, query: SalesRecordQuery) -> SalesRecordListData:
        """
        获取销售记录列表
        
        Args:
            db: 数据库会话
            query: 查询参数
            
        Returns:
            SalesRecordListData: 包含销售记录列表、分页信息和汇总信息的数据
        """
        try:
            # 构建参数字典
            params = {}
            
            # 构建WITH子句的过滤条件
            name_filter = ""
            if query.name:
                name_filter = "o.name LIKE :name_filter OR p.name LIKE :name_filter"
                params["name_filter"] = f"%{query.name}%"
            else:
                name_filter = "1=1"  # 如果没有提供name参数，则不进行过滤
            
            # 构建基本的SQL查询
            base_sql = f"""
            WITH matched_org AS (
                SELECT
                    o.id AS org_id,
                    o.parent_id,
                    p.name AS parent_name,
                    p.sort AS parent_sort,
                    o.sort AS org_sort 
                FROM
                    orgs AS o
                    LEFT JOIN orgs AS p ON p.id = o.parent_id 
                WHERE
                    {name_filter}
            ) 
            SELECT
                s.*,
                m.parent_id,
                m.parent_name 
            FROM
                sales_records AS s
                JOIN orgs AS o_map ON o_map.name = s.warehouse_name
                JOIN matched_org AS m ON m.org_id = o_map.id 
            """
            
            # 添加其他过滤条件
            where_clauses = []
            
            if query.start_date:
                where_clauses.append("s.date >= :start_date")
                params["start_date"] = query.start_date
                
            if query.end_date:
                where_clauses.append("s.date <= :end_date")
                params["end_date"] = query.end_date
                
            if query.platform:
                where_clauses.append("s.platform = :platform")
                params["platform"] = query.platform
                
            # 添加是否显示无数据门店的过滤条件
            if not query.show_empty_poi:
                where_clauses.append("s.sales_cart_count > 0")
            
            # 如果有额外的过滤条件，添加WHERE子句
            if where_clauses:
                base_sql += " WHERE " + " AND ".join(where_clauses)
            
            # 构建计数查询
            count_sql = f"""
            SELECT COUNT(*) as total_count
            FROM (
                {base_sql}
            ) as filtered_records
            """
            
            # 执行计数查询
            total_count_result = db.execute(text(count_sql), params).scalar()
            total = total_count_result or 0
            
            # 添加排序和分页
            full_sql = f"""
            {base_sql}
            ORDER BY
                s.date DESC,
                m.parent_sort,
                m.org_sort
            LIMIT :limit OFFSET :offset
            """
            
            # 添加分页参数
            params["limit"] = query.limit
            params["offset"] = query.skip
            
            # 执行查询
            results = db.execute(text(full_sql), params).all()
            
            # 构建汇总查询
            summary_sql = f"""
            WITH matched_org AS (
                SELECT
                    o.id AS org_id,
                    o.parent_id,
                    p.name AS parent_name,
                    p.sort AS parent_sort,
                    o.sort AS org_sort 
                FROM
                    orgs AS o
                    LEFT JOIN orgs AS p ON p.id = o.parent_id 
                WHERE
                    {name_filter}
            ) 
            SELECT
                SUM(s.income_amt) as total_income,
                SUM(s.sales_cart_count) as total_cart_count
            FROM
                sales_records AS s
                JOIN orgs AS o_map ON o_map.name = s.warehouse_name
                JOIN matched_org AS m ON m.org_id = o_map.id 
            """
            
            # 如果有额外的过滤条件，添加WHERE子句
            if where_clauses:
                summary_sql += " WHERE " + " AND ".join(where_clauses)
            
            # 执行汇总查询
            summary_result = db.execute(text(summary_sql), params).first()
            
            # 计算分页信息
            page_no = (query.skip // query.limit) + 1
            total_page_size = math.ceil(total / query.limit) if total > 0 else 1
            
            page_info = PageInfo(
                pageNo=page_no,
                pageSize=query.limit,
                totalCount=total,
                totalPageSize=total_page_size
            )
            
            # 处理汇总数据
            total_income = summary_result.total_income if summary_result and summary_result.total_income else 0
            total_cart_count = summary_result.total_cart_count if summary_result and summary_result.total_cart_count else 0
            
            # 使用Decimal进行除法运算，并四舍五入保留两位小数
            if total_cart_count > 0:
                # 确保使用Decimal类型进行计算
                income_decimal = Decimal(str(total_income))
                count_decimal = Decimal(str(total_cart_count))
                avg_income = income_decimal / count_decimal
                # 四舍五入保留两位小数
                avg_income = avg_income.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:
                avg_income = Decimal('0.00')
            
            summary = SalesRecordSummary(
                income_amt=str(total_income),
                sales_cart_count=str(total_cart_count),
                avg_income_amt=str(avg_income)
            )
            
            # 转换查询结果为响应模型
            items = []
            for record in results:
                # 转换数据库结果为字典
                record_dict = {
                    "id": record.id,
                    "date": record.date,
                    "platform": record.platform,
                    "warehouse_name": record.warehouse_name,
                    "income_amt": record.income_amt,
                    "sales_cart_count": record.sales_cart_count,
                    "avg_income_amt": record.avg_income_amt,
                    "created_at": record.created_at,
                    "updated_at": record.updated_at
                }
                # 创建响应模型
                items.append(SalesRecordResponse.model_validate(record_dict))
            
            return SalesRecordListData(
                items=items,
                pageInfo=page_info,
                summary=summary
            )
            
        except SQLAlchemyError as e:
            logger.error(f"查询销售记录列表出错: {str(e)}")
            raise
    
    @staticmethod
    def create_sales_record(db: Session, record: SalesRecordCreate) -> SalesRecord:
        """
        创建销售记录
        
        Args:
            db: 数据库会话
            record: 销售记录创建模型
            
        Returns:
            SalesRecord: 创建的销售记录
        """
        try:
            # 检查是否已存在相同平台、日期和仓库的记录
            existing_record = db.query(SalesRecord).filter(
                SalesRecord.platform == record.platform,
                SalesRecord.date == record.date,
                SalesRecord.warehouse_name == record.warehouse_name
            ).first()
            
            if existing_record:
                # 如果记录已存在，抛出异常
                raise ValueError(f"该日期({record.date})、平台({record.platform})和仓库({record.warehouse_name})的销售记录已存在")
            
            db_record = SalesRecord(
                date=record.date,
                platform=record.platform,
                warehouse_name=record.warehouse_name,
                income_amt=record.income_amt,
                sales_cart_count=record.sales_cart_count,
                avg_income_amt=record.avg_income_amt
            )
            db.add(db_record)
            db.commit()
            db.refresh(db_record)
            return db_record
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"创建销售记录出错: {str(e)}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"创建销售记录失败: {str(e)}")
            raise
    
    @staticmethod
    def update_sales_record(db: Session, record_id: int, record: SalesRecordUpdate) -> Optional[SalesRecord]:
        """
        更新销售记录
        
        Args:
            db: 数据库会话
            record_id: 记录ID
            record: 销售记录更新模型
            
        Returns:
            Optional[SalesRecord]: 更新后的销售记录，不存在则返回None
        """
        try:
            db_record = RecordService.get_sales_record(db, record_id)
            if not db_record:
                return None
            
            update_data = record.dict(exclude_unset=True)
            
            # 如果更新了平台、日期或仓库名称，需要检查是否与其他记录冲突
            if "platform" in update_data or "date" in update_data or "warehouse_name" in update_data:
                # 获取更新后的值
                updated_platform = update_data.get("platform", db_record.platform)
                updated_date = update_data.get("date", db_record.date)
                updated_warehouse_name = update_data.get("warehouse_name", db_record.warehouse_name)
                
                # 检查是否已存在相同平台、日期和仓库的记录（排除当前记录）
                existing_record = db.query(SalesRecord).filter(
                    SalesRecord.platform == updated_platform,
                    SalesRecord.date == updated_date,
                    SalesRecord.warehouse_name == updated_warehouse_name,
                    SalesRecord.id != record_id
                ).first()
                
                if existing_record:
                    # 如果记录已存在，抛出异常
                    raise ValueError(f"该日期({updated_date})、平台({updated_platform})和仓库({updated_warehouse_name})的销售记录已存在")
            
            # 更新记录
            for key, value in update_data.items():
                setattr(db_record, key, value)
            
            db.commit()
            db.refresh(db_record)
            return db_record
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"更新销售记录出错: {str(e)}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"更新销售记录失败: {str(e)}")
            raise
    
    @staticmethod
    def delete_sales_record(db: Session, record_id: int) -> bool:
        """
        删除销售记录
        
        Args:
            db: 数据库会话
            record_id: 记录ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            db_record = RecordService.get_sales_record(db, record_id)
            if not db_record:
                return False
            
            db.delete(db_record)
            db.commit()
            return True
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"删除销售记录出错: {str(e)}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"删除销售记录失败: {str(e)}")
            raise 
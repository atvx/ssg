from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Dict, Any
from datetime import date as date_type
import logging

from models.sales import SalesRecord
from schemas.record import SalesRecordCreate, SalesRecordUpdate, SalesRecordQuery

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
    def get_sales_records(db: Session, query: SalesRecordQuery) -> tuple[List[SalesRecord], int]:
        """
        获取销售记录列表
        
        Args:
            db: 数据库会话
            query: 查询参数
            
        Returns:
            tuple[List[SalesRecord], int]: 销售记录列表和总记录数
        """
        try:
            # 构建查询
            db_query = db.query(SalesRecord)
            
            # 应用筛选条件
            if query.start_date:
                db_query = db_query.filter(SalesRecord.date >= query.start_date)
            if query.end_date:
                db_query = db_query.filter(SalesRecord.date <= query.end_date)
            if query.platform:
                db_query = db_query.filter(SalesRecord.platform == query.platform)
            if query.warehouse_name:
                db_query = db_query.filter(SalesRecord.warehouse_name == query.warehouse_name)
            
            # 获取总记录数
            total = db_query.count()
            
            # 应用分页
            records = db_query.order_by(SalesRecord.date.desc()) \
                .offset(query.skip).limit(query.limit).all()
            
            return records, total
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
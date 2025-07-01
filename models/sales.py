from sqlalchemy import Column, Integer, String, Date, DateTime, DECIMAL, UniqueConstraint
from sqlalchemy.sql import func

from db.database import Base


class SalesRecord(Base):
    __tablename__ = "sales_records"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True, nullable=False)
    platform = Column(String(20), index=True, nullable=False)  # "meituan" 或 "duowei"
    warehouse_name = Column(String(100), index=True, nullable=False)  # 仓库名称
    income_amt = Column(DECIMAL(10, 2), nullable=False)  # 收入金额
    sales_cart_count = Column(Integer, nullable=False)   # 销售数量
    avg_income_amt = Column(DECIMAL(10, 2), nullable=False)  # 平均收入
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 使用平台+日期+仓库名称作为唯一约束
    __table_args__ = (
        UniqueConstraint('platform', 'date', 'warehouse_name', name='uix_sales_record'),
    )

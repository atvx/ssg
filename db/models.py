from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text, Float, Date, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base

class MonthlySalesTarget(Base):
    """月度销售目标数据库模型"""
    __tablename__ = "sales_target"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    org_id = Column(String(50), index=True, nullable=False)
    org_name = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    target_income = Column(Numeric(18, 2), nullable=False)
    car_count = Column(Integer, nullable=True)  # 车辆数量
    actual_income = Column(Numeric(18, 2), nullable=True)  # 实际收入
    ach_rate = Column(Numeric(3, 1), nullable=True)  # 达成率
    sold_car_count = Column(Integer, nullable=True)  # 销售车辆数
    per_car_income = Column(Numeric(18, 2), nullable=True)  # 车均收入
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Org(Base):
    """机构表数据库模型"""
    __tablename__ = "orgs"

    id = Column(String(50), primary_key=True, index=True, comment="机构编号")
    parent_id = Column(String(50), ForeignKey("orgs.id"), nullable=True, index=True, comment="父级机构编号")
    parent_name = Column(String(50), nullable=True, comment="父级机构名称")
    org_type = Column(Integer, nullable=True, comment="机构类型")
    org_code = Column(String(50), nullable=True, comment="机构代码")
    tenant_id = Column(String(50), nullable=True, index=True, comment="租户编号")
    name = Column(String(255), nullable=True, comment="机构名称")
    poi_id = Column(String(50), nullable=True, comment="门店编号")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    sort = Column(Integer, nullable=True, comment="排序")
    platform = Column(String(20), nullable=True, comment="平台")
    status = Column(Integer, default=1, nullable=True, comment="状态（0禁用/1正常）")
    per_car_target = Column(Integer, nullable=True, comment="车均目标")
    cost_rate = Column(Numeric(3, 2), nullable=False, default=0, comment="成本率")

    children = relationship("Org", backref="parent", remote_side=[id]) 
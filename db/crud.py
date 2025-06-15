import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import json
from sqlalchemy import and_, or_, desc, select
from decimal import Decimal

from . import models
from models.user import User
from models.task import Task
from models.sales import SalesRecord
from models.ext_account import ExtAccount
from schemas import user as user_schema
from schemas import sales as sales_schema
from schemas import task as task_schema
from schemas import org as org_schema
from schemas.user import UserCreate, UserUpdate
from schemas.task import TaskCreate
from schemas.sales import MonthlySalesTargetCreate, MonthlySalesTargetUpdate
from utils.security import get_password_hash, verify_password

# 配置日志
logger = logging.getLogger(__name__)

# 用户相关操作
def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def get_user_by_mobile(db: Session, mobile: str):
    """根据手机号获取用户"""
    if not mobile:
        return None
    return db.query(User).filter(User.mobile == mobile).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user: user_schema.UserCreate):
    """创建新用户"""
    # 检查用户名和手机号是否已存在
    existing_username = get_user_by_username(db, user.username)
    if existing_username:
        raise ValueError(f"用户名 '{user.username}' 已被注册")
    
    if user.mobile:
        existing_mobile = get_user_by_mobile(db, user.mobile)
        if existing_mobile:
            raise ValueError(f"手机号 '{user.mobile}' 已被注册")
    
    # 生成密码哈希
    hashed_password = get_password_hash(user.password)
    
    # 创建用户对象
    db_user = User(
        username=user.username,
        mobile=user.mobile,
        hashed_password=hashed_password,
        is_active=False,  # 默认未激活
        is_superuser=False,  # 默认非超级用户
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        # 重新抛出异常，让上层处理
        raise e


def update_user(db: Session, user_id: int, user: user_schema.UserUpdate):
    db_user = get_user(db, user_id)
    update_data = user.dict(exclude_unset=True)
    
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    # 检查手机号是否已存在
    if "mobile" in update_data and update_data["mobile"]:
        existing_user = get_user_by_mobile(db, update_data["mobile"])
        if existing_user and existing_user.id != user_id:
            raise ValueError(f"手机号 '{update_data['mobile']}' 已被其他用户使用")
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    try:
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        raise e


def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def delete_user(db: Session, user_id: int):
    user = get_user(db, user_id)
    if not user:
        return None
    
    try:
        db.delete(user)
        db.commit()
        return user
    except Exception as e:
        db.rollback()
        raise e


# 销售数据相关操作
def get_sales_records(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    platform: Optional[str] = None,
    warehouse_name: Optional[str] = None
):
    """
    获取销售记录，支持多种筛选条件
    
    Args:
        db: 数据库会话
        skip: 跳过的记录数
        limit: 返回的最大记录数
        start_date: 开始日期
        end_date: 结束日期
        platform: 平台名称
        warehouse_name: 仓库名称
        
    Returns:
        List[SalesRecord]: 销售记录列表
    """
    try:
        query = db.query(SalesRecord)
        
        if start_date:
            query = query.filter(SalesRecord.date >= start_date)
        if end_date:
            query = query.filter(SalesRecord.date <= end_date)
        if platform:
            query = query.filter(SalesRecord.platform == platform)
        if warehouse_name:
            query = query.filter(SalesRecord.warehouse_name == warehouse_name)
        
        return query.order_by(SalesRecord.date.desc()).offset(skip).limit(limit).all()
    except SQLAlchemyError as e:
        logger.error(f"获取销售记录数据库错误: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"获取销售记录失败: {str(e)}")
        raise


def get_sales_record_by_date_platform_warehouse(
    db: Session, 
    record_date: date,
    platform: str,
    warehouse_name: str
):
    """
    根据日期、平台和仓库获取特定的销售记录
    
    Args:
        db: 数据库会话
        record_date: 记录日期
        platform: 平台名称
        warehouse_name: 仓库名称
        
    Returns:
        Optional[SalesRecord]: 销售记录，如果不存在则返回None
    """
    try:
        return db.query(SalesRecord).filter(
            SalesRecord.date == record_date,
            SalesRecord.platform == platform,
            SalesRecord.warehouse_name == warehouse_name
        ).first()
    except SQLAlchemyError as e:
        logger.error(f"查询特定销售记录数据库错误: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"查询特定销售记录失败: {str(e)}")
        raise


def create_sales_record(db: Session, record: sales_schema.SalesRecordCreate):
    """
    创建新的销售记录
    
    Args:
        db: 数据库会话
        record: 销售记录创建模型
        
    Returns:
        SalesRecord: 创建的销售记录
    """
    try:
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
        logger.error(f"创建销售记录数据库错误: {str(e)}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建销售记录失败: {str(e)}")
        raise


def create_or_update_sales_record(db: Session, record: sales_schema.SalesRecordCreate):
    """
    创建或更新销售记录
    
    Args:
        db: 数据库会话
        record: 销售记录创建模型
        
    Returns:
        SalesRecord: 创建或更新的销售记录
    """
    try:
        db_record = get_sales_record_by_date_platform_warehouse(
            db, record.date, record.platform, record.warehouse_name
        )
        
        if db_record:
            # 更新现有记录
            db_record.income_amt = record.income_amt
            db_record.sales_cart_count = record.sales_cart_count
            db_record.avg_income_amt = record.avg_income_amt
            db.commit()
            db.refresh(db_record)
            return db_record
        else:
            # 创建新记录
            return create_sales_record(db, record)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"创建或更新销售记录数据库错误: {str(e)}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建或更新销售记录失败: {str(e)}")
        raise


def get_warehouses(db: Session, platform: Optional[str] = None):
    """
    获取仓库列表
    
    Args:
        db: 数据库会话
        platform: 可选的平台筛选
        
    Returns:
        List[Dict]: 仓库列表，每个元素包含name和platform字段
    """
    try:
        query = db.query(SalesRecord.warehouse_name, SalesRecord.platform).distinct()
        if platform:
            query = query.filter(SalesRecord.platform == platform)
        
        results = query.all()
        return [{"name": row[0], "platform": row[1]} for row in results]
    except SQLAlchemyError as e:
        logger.error(f"获取仓库列表数据库错误: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"获取仓库列表失败: {str(e)}")
        raise


# 认证会话相关操作
def get_active_auth_session(db: Session, platform: str):
    return db.query(models.AuthSession).filter(
        models.AuthSession.platform == platform,
        models.AuthSession.status == "active"
    ).order_by(models.AuthSession.created_at.desc()).first()


def create_auth_session(db: Session, platform: str, status: str, cookies: Optional[str] = None):
    db_session = models.AuthSession(
        platform=platform,
        status=status,
        cookies=cookies,
        created_at=datetime.utcnow(),
        last_used=datetime.utcnow()
    )
    if status == "active":
        db_session.expires_at = datetime.utcnow() + datetime.timedelta(days=7)
    
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def update_auth_session(db: Session, session_id: int, status: str, cookies: Optional[str] = None):
    db_session = db.query(models.AuthSession).filter(models.AuthSession.id == session_id).first()
    if db_session:
        db_session.status = status
        if cookies:
            db_session.cookies = cookies
        db_session.last_used = datetime.utcnow()
        if status == "active":
            db_session.expires_at = datetime.utcnow() + datetime.timedelta(days=7)
        db.commit()
        db.refresh(db_session)
    return db_session


# 任务相关操作
def create_task(db: Session, task: task_schema.TaskCreate, user_id: int):
    db_task = Task(
        task_type=task.task_type,
        status="pending",
        progress=0,
        user_id=user_id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_task(db: Session, task_id: int):
    return db.query(Task).filter(Task.id == task_id).first()


def get_tasks_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(Task).filter(Task.user_id == user_id).order_by(
        Task.created_at.desc()
    ).offset(skip).limit(limit).all()


def update_task(db: Session, task_id: int, task_update):
    """更新任务信息"""
    db_task = get_task(db, task_id)
    if not db_task:
        logger.warning(f"Task with id {task_id} not found")
        return None
    
    # 判断task_update是普通字典还是Pydantic模型
    if hasattr(task_update, 'dict'):
        # Pydantic模型
        update_data = task_update.dict(exclude_unset=True)
    else:
        # 普通字典
        update_data = task_update
    
    for key, value in update_data.items():
        setattr(db_task, key, value)
    
    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(db: Session, task_id: int):
    """删除任务"""
    db_task = get_task(db, task_id)
    if not db_task:
        raise ValueError(f"Task with id {task_id} not found")
    
    db.delete(db_task)
    db.commit()
    return db_task


# 月度销售目标CRUD操作
def create_monthly_sales_target(db: Session, target: MonthlySalesTargetCreate) -> models.MonthlySalesTarget:
    """创建新的月度销售目标"""
    db_target = models.MonthlySalesTarget(
        org_id=target.org_id,
        year=target.year,
        month=target.month,
        target_income=target.target_income
    )
    db.add(db_target)
    db.commit()
    db.refresh(db_target)
    return db_target


def get_sales_targets(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    org_id: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None
) -> List[models.MonthlySalesTarget]:
    """获取月度销售目标列表，支持筛选"""
    query = db.query(models.MonthlySalesTarget)
    
    # 应用筛选条件
    if org_id:
        query = query.filter(models.MonthlySalesTarget.org_id == org_id)
    if year:
        query = query.filter(models.MonthlySalesTarget.year == year)
    if month:
        query = query.filter(models.MonthlySalesTarget.month == month)
    
    # 按年月和排序字段排序
    query = query.order_by(
        desc(models.MonthlySalesTarget.year), 
        desc(models.MonthlySalesTarget.month)
    )
    
    return query.offset(skip).limit(limit).all()


def get_monthly_sales_target(db: Session, target_id: int) -> Optional[models.MonthlySalesTarget]:
    """根据ID获取单个月度销售目标"""
    return db.query(models.MonthlySalesTarget).filter(models.MonthlySalesTarget.id == target_id).first()


def update_monthly_sales_target(
    db: Session, 
    target_id: int, 
    target_update: MonthlySalesTargetUpdate
) -> Optional[models.MonthlySalesTarget]:
    """更新月度销售目标"""
    db_target = get_monthly_sales_target(db, target_id)
    if not db_target:
        return None
    
    update_data = target_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_target, key, value)
    
    db.commit()
    db.refresh(db_target)
    return db_target


def delete_monthly_sales_target(db: Session, target_id: int) -> bool:
    """删除月度销售目标"""
    db_target = get_monthly_sales_target(db, target_id)
    if not db_target:
        return False
    
    db.delete(db_target)
    db.commit()
    return True


# 机构相关操作
def get_orgs(db: Session, skip: int = 0, limit: int = 100):
    """获取机构列表"""
    return db.query(models.Org).offset(skip).limit(limit).all()


def get_org(db: Session, org_id: str):
    """根据ID获取单个机构"""
    return db.query(models.Org).filter(models.Org.id == org_id).first()


def create_org(db: Session, org: org_schema.OrgCreate):
    """创建新的机构"""
    # 检查机构名是否已存在
    existing_org = db.query(models.Org).filter(models.Org.name == org.name).first()
    if existing_org:
        raise ValueError(f"机构名 '{org.name}' 已被注册")
    
    # 检查ID是否已存在
    existing_id = db.query(models.Org).filter(models.Org.id == org.id).first()
    if existing_id:
        raise ValueError(f"机构ID '{org.id}' 已被使用")
    
    # 创建机构对象，只包含允许的字段
    db_org = models.Org(
        id=org.id,
        name=org.name,
        org_type=org.org_type,
        parent_id=org.parent_id,
        sort=org.sort,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    try:
        db.add(db_org)
        db.commit()
        db.refresh(db_org)
        return db_org
    except Exception as e:
        db.rollback()
        # 重新抛出异常，让上层处理
        raise e


def update_org(db: Session, org_id: str, org: org_schema.OrgUpdate):
    """更新机构信息，只更新允许的字段"""
    db_org = get_org(db, org_id)
    if not db_org:
        raise ValueError(f"找不到ID为'{org_id}'的机构")
    
    # 只更新允许的字段
    update_data = org.dict(exclude_unset=True)
    allowed_fields = {"name", "org_type", "parent_id", "sort"}
    
    for key, value in update_data.items():
        if key in allowed_fields:
            setattr(db_org, key, value)
    
    try:
        db.commit()
        db.refresh(db_org)
        return db_org
    except Exception as e:
        db.rollback()
        raise e


def delete_org(db: Session, org_id: str) -> bool:
    """删除机构"""
    db_org = get_org(db, org_id)
    if not db_org:
        return False
    
    # 检查是否有子机构引用该机构
    child_orgs = db.query(models.Org).filter(models.Org.parent_id == org_id).first()
    if child_orgs:
        raise ValueError(f"无法删除该机构，存在引用该机构作为父级机构的子机构")
    
    db.delete(db_org)
    db.commit()
    return True


def get_org_list(db: Session, skip: int = 0, limit: int = 100, org_types: Optional[List[str]] = None):
    """
    获取机构列表，按指定的字段返回
    
    参数:
        db: 数据库会话
        skip: 跳过的记录数，默认为0
        limit: 返回的最大记录数，默认为100
        org_types: 机构类型列表，支持多选，默认为None表示不过滤
        
    返回:
        List[Dict]: 机构列表，每个元素包含org_id, org_name, org_type, parent_id, sort字段
    """
    try:
        # 使用SQLAlchemy的查询
        # MySQL不支持NULLS FIRST语法，使用CASE WHEN方式处理NULL值排序
        query = db.query(
            models.Org.id.label('org_id'),
            models.Org.name.label('org_name'),
            models.Org.org_type,
            models.Org.parent_id,
            models.Org.sort
        )
        
        # 应用org_types过滤条件
        if org_types and len(org_types) > 0:
            query = query.filter(models.Org.org_type.in_(org_types))
        
        # 排序
        query = query.order_by(
            # 先按NULL值排序（NULL值在前），然后按sort字段升序排序
            models.Org.sort.is_(None).desc(),
            models.Org.sort.asc()
        )
        
        # 执行查询
        result = query.offset(skip).limit(limit).all()
        
        # 将结果转换为字典列表
        orgs = []
        for row in result:
            org_dict = {
                'org_id': row.org_id,
                'org_name': row.org_name,
                'org_type': row.org_type,
                'parent_id': row.parent_id,
                'sort': row.sort
            }
            orgs.append(org_dict)
        
        return orgs
    except SQLAlchemyError as e:
        logger.error(f"获取机构列表数据库错误: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"获取机构列表失败: {str(e)}")
        raise


# 外部账号相关操作
def get_ext_account(db: Session, account_id: int) -> Optional[ExtAccount]:
    """
    根据ID获取外部账号
    
    Args:
        db: 数据库会话
        account_id: 账号ID
        
    Returns:
        Optional[ExtAccount]: 找到的账号，不存在则返回None
    """
    return db.query(ExtAccount).filter(ExtAccount.id == account_id).first()

def get_ext_accounts_by_user(db: Session, user_id: int) -> List[ExtAccount]:
    """
    获取用户的所有外部账号
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        
    Returns:
        List[ExtAccount]: 账号列表
    """
    return db.query(ExtAccount).filter(ExtAccount.user_id == user_id).all()

def get_ext_account_by_platform(db: Session, user_id: int, platform: str) -> Optional[ExtAccount]:
    """
    获取用户特定平台的外部账号
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        platform: 平台名称
        
    Returns:
        Optional[ExtAccount]: 找到的账号，不存在则返回None
    """
    return db.query(ExtAccount).filter(
        ExtAccount.user_id == user_id,
        ExtAccount.platform == platform
    ).first()

def create_ext_account(db: Session, user_id: int, platform: str, username: str, password: str) -> ExtAccount:
    """
    创建外部账号
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        platform: 平台名称
        username: 用户名
        password: 密码
        
    Returns:
        ExtAccount: 创建的账号
    """
    # 检查是否已存在同平台账号
    existing = get_ext_account_by_platform(db, user_id, platform)
    if existing:
        raise ValueError(f"用户已有{platform}平台账号")
    
    # 创建新账号
    account = ExtAccount(
        user_id=user_id,
        platform=platform,
        username=username,
        password=password  # 注意：实际应用中应该加密存储
    )
    
    try:
        db.add(account)
        db.commit()
        db.refresh(account)
        return account
    except Exception as e:
        db.rollback()
        raise e

def update_ext_account(db: Session, account_id: int, username: Optional[str] = None, password: Optional[str] = None) -> Optional[ExtAccount]:
    """
    更新外部账号
    
    Args:
        db: 数据库会话
        account_id: 账号ID
        username: 新用户名（可选）
        password: 新密码（可选）
        
    Returns:
        Optional[ExtAccount]: 更新后的账号，不存在则返回None
    """
    account = get_ext_account(db, account_id)
    if not account:
        return None
    
    if username:
        account.username = username
    if password:
        account.password = password
    
    try:
        db.commit()
        db.refresh(account)
        return account
    except Exception as e:
        db.rollback()
        raise e

def delete_ext_account(db: Session, account_id: int) -> bool:
    """
    删除外部账号
    
    Args:
        db: 数据库会话
        account_id: 账号ID
        
    Returns:
        bool: 删除成功返回True，否则返回False
    """
    account = get_ext_account(db, account_id)
    if not account:
        return False
    
    try:
        db.delete(account)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e


# 日报相关数据库操作
def get_daily_sales_data(db: Session, query_date: str) -> List[Dict[str, Any]]:
    """
    获取指定日期的销售数据，用于生成日报
    
    Args:
        db: 数据库会话
        query_date: 查询日期，格式为 YYYY-MM-DD
        
    Returns:
        List[Dict]: 销售数据列表
    """
    try:
        from datetime import datetime
        from sqlalchemy import text
        
        # 获取年月信息
        date_obj = datetime.strptime(query_date, '%Y-%m-%d')
        current_year = date_obj.year
        current_month = date_obj.month
        
        # 构建SQL查询 - 使用text()来执行原生SQL
        sql_query = text("""
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
        LEFT JOIN sales_target t ON t.org_name = s.warehouse_name AND t.year = :current_year AND t.month = :current_month
        WHERE c.org_type = 3 AND s.date = :query_date
        ORDER BY p.sort ASC, c.sort ASC
        """)
        
        result = db.execute(sql_query, {
            'current_year': current_year,
            'current_month': current_month,
            'query_date': query_date
        })
        
        # 将结果转换为字典列表
        columns = result.keys()
        rows = result.fetchall()
        
        return [dict(zip(columns, row)) for row in rows]
        
    except SQLAlchemyError as e:
        logger.error(f"获取日报销售数据数据库错误: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"获取日报销售数据失败: {str(e)}")
        raise

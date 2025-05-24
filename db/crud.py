from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import json
import logging

from models.user import User
from models.sales import SalesRecord
from models.auth import AuthSession
from models.task import Task
from schemas import user as user_schema
from schemas import sales as sales_schema
from schemas import task as task_schema
from utils.security import get_password_hash, verify_password

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    return db.query(AuthSession).filter(
        AuthSession.platform == platform,
        AuthSession.status == "active"
    ).order_by(AuthSession.created_at.desc()).first()


def create_auth_session(db: Session, platform: str, status: str, cookies: Optional[str] = None):
    db_session = AuthSession(
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
    db_session = db.query(AuthSession).filter(AuthSession.id == session_id).first()
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
        raise ValueError(f"Task with id {task_id} not found")
    
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

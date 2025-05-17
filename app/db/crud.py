from datetime import datetime, date
from typing import List, Optional
from sqlalchemy.orm import Session
import json

from app.models.user import User
from app.models.sales import SalesRecord
from app.models.auth import AuthSession
from app.models.task import Task
from app.schemas import user as user_schema
from app.schemas import sales as sales_schema
from app.schemas import task as task_schema
from app.utils.security import get_password_hash, verify_password


# 用户相关操作
def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user: user_schema.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        mobile=user.mobile,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user: user_schema.UserUpdate):
    db_user = get_user(db, user_id)
    update_data = user.dict(exclude_unset=True)
    
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user


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


def get_sales_record_by_date_platform_warehouse(
    db: Session, 
    record_date: date,
    platform: str,
    warehouse_name: str
):
    return db.query(SalesRecord).filter(
        SalesRecord.date == record_date,
        SalesRecord.platform == platform,
        SalesRecord.warehouse_name == warehouse_name
    ).first()


def create_sales_record(db: Session, record: sales_schema.SalesRecordCreate):
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


def create_or_update_sales_record(db: Session, record: sales_schema.SalesRecordCreate):
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


def get_warehouses(db: Session, platform: Optional[str] = None):
    query = db.query(SalesRecord.warehouse_name, SalesRecord.platform).distinct()
    if platform:
        query = query.filter(SalesRecord.platform == platform)
    
    results = query.all()
    return [{"name": row[0], "platform": row[1]} for row in results]


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


def update_task(db: Session, task_id: int, task_update: task_schema.TaskUpdate):
    db_task = get_task(db, task_id)
    if not db_task:
        return None
    
    update_data = task_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    
    if task_update.status == "completed" and not db_task.completed_at:
        db_task.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_task)
    return db_task

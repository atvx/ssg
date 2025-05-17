import json
from datetime import datetime, date
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session

from app.celery_app.celery import celery_app
from app.db.database import SessionLocal
from app.db.crud import update_task, create_or_update_sales_record
from app.schemas.sales import SalesRecordCreate
from app.services.meituan_service import fetch_meituan_data
from app.services.duowei_service import fetch_duowei_data

logger = get_task_logger(__name__)


# 辅助函数，用于更新任务状态
def update_task_status(task_id: int, status: str, progress: int, result=None, error=None):
    db = SessionLocal()
    try:
        task_update = {
            "status": status,
            "progress": progress
        }
        if result:
            task_update["result"] = json.dumps(result, ensure_ascii=False)
        if error:
            task_update["error"] = error
        
        update_task(db, task_id, task_update)
    finally:
        db.close()


# 保存销售记录到数据库
def save_sales_records(records, platform, date_str):
    db = SessionLocal()
    try:
        for record in records:
            sales_record = SalesRecordCreate(
                date=date.fromisoformat(date_str),
                platform=platform,
                warehouse_name=record["name"],
                income_amt=record["incomeAmt"],
                sales_cart_count=record["salesCartCount"],
                avg_income_amt=record["avgIncomeAmt"]
            )
            create_or_update_sales_record(db, sales_record)
    finally:
        db.close()


@celery_app.task(bind=True)
def fetch_meituan_task(self, task_id: int, date_str: str = None):
    """获取美团数据的后台任务"""
    try:
        update_task_status(task_id, "running", 10)
        
        # 获取数据
        data = fetch_meituan_data(date_str)
        update_task_status(task_id, "running", 50)
        
        # 保存数据到数据库
        save_sales_records(data, "meituan", date_str or datetime.now().strftime("%Y-%m-%d"))
        
        # 更新任务状态
        update_task_status(task_id, "completed", 100, result=data)
        
        return {"status": "success", "data": data}
    except Exception as e:
        logger.error(f"获取美团数据失败: {str(e)}")
        update_task_status(task_id, "failed", 0, error=str(e))
        return {"status": "error", "error": str(e)}


@celery_app.task(bind=True)
def fetch_duowei_task(self, task_id: int, date_str: str = None):
    """获取多维数据的后台任务"""
    try:
        update_task_status(task_id, "running", 10)
        
        # 获取数据
        data = fetch_duowei_data(date_str)
        update_task_status(task_id, "running", 50)
        
        # 保存数据到数据库
        save_sales_records(data, "duowei", date_str or datetime.now().strftime("%Y-%m-%d"))
        
        # 更新任务状态
        update_task_status(task_id, "completed", 100, result=data)
        
        return {"status": "success", "data": data}
    except Exception as e:
        logger.error(f"获取多维数据失败: {str(e)}")
        update_task_status(task_id, "failed", 0, error=str(e))
        return {"status": "error", "error": str(e)}


@celery_app.task(bind=True)
def fetch_all_data_task(self, task_id: int, date_str: str = None):
    """获取所有平台数据的后台任务"""
    try:
        update_task_status(task_id, "running", 10)
        
        # 获取美团数据
        meituan_data = fetch_meituan_data(date_str)
        update_task_status(task_id, "running", 40)
        
        # 获取多维数据
        duowei_data = fetch_duowei_data(date_str)
        update_task_status(task_id, "running", 70)
        
        # 合并数据
        all_data = meituan_data + duowei_data
        
        # 保存数据到数据库
        today = date_str or datetime.now().strftime("%Y-%m-%d")
        save_sales_records(meituan_data, "meituan", today)
        save_sales_records(duowei_data, "duowei", today)
        
        # 更新任务状态
        update_task_status(task_id, "completed", 100, result=all_data)
        
        return {"status": "success", "data": all_data}
    except Exception as e:
        logger.error(f"获取所有平台数据失败: {str(e)}")
        update_task_status(task_id, "failed", 0, error=str(e))
        return {"status": "error", "error": str(e)}

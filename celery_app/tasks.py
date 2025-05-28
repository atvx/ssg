import logging
import json
from datetime import datetime, date
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session

from celery import shared_task
from celery_app.celery import celery_app
from db.database import SessionLocal, get_db
from db.crud import update_task, create_or_update_sales_record, get_task
from models.task import Task
from schemas.sales import SalesRecordCreate
from schemas.task import TaskUpdate
from services.meituan_service import fetch_meituan_data
from services.duowei_service import fetch_duowei_data

# 配置日志
logger = logging.getLogger(__name__)


# 辅助函数，用于更新任务状态
def update_task_status(task_id: int, status: str, progress: int, result=None, error=None):
    db = SessionLocal()
    try:
        # 先检查任务是否存在
        task = get_task(db, task_id)
        if not task:
            logger.warning(f"尝试更新不存在的任务: Task with id {task_id} not found")
            return False
            
        # 使用TaskUpdate模型而不是普通字典
        task_update_data = {
            "status": status,
            "progress": progress
        }
        if result:
            task_update_data["result"] = json.dumps(result, ensure_ascii=False)
        if error:
            task_update_data["error"] = error
        
        # 创建TaskUpdate模型实例
        task_update = TaskUpdate(**task_update_data)
        
        update_task(db, task_id, task_update)
        return True
    except Exception as e:
        logger.error(f"更新任务状态失败: {str(e)}")
        return False
    finally:
        db.close()


# 保存销售记录到数据库
def save_sales_records(records, platform, date_str):
    # 确保在函数内部可以访问date
    from datetime import date
    
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
def fetch_meituan_task(self, task_id: int, date: str = None):
    """获取美团数据的后台任务"""
    # 确保在函数内部可以访问datetime
    from datetime import datetime
    
    try:
        # 检查任务是否存在，如果不存在则提前返回
        if not update_task_status(task_id, "running", 10):
            logger.error(f"任务不存在: Task with id {task_id} not found")
            return {"status": "error", "error": f"Task with id {task_id} not found"}
        
        # 使用Meituan服务获取数据
        from services.meituan_service import fetch_meituan_data
        db = next(get_db())
        
        # 获取任务对象，以便获取用户ID
        from db.crud import get_task
        task = get_task(db, task_id)
        user_id = task.user_id if task else None
        
        # 获取美团数据
        data = fetch_meituan_data(db, date, user_id)
        update_task_status(task_id, "running", 50)
        
        # 检查是否获取成功
        if not data["success"]:
            update_task_status(task_id, "failed", 0, error=data["message"])
            return {"status": "error", "error": data["message"]}
        
        # 保存数据到数据库
        # 使用date作为默认日期，如果未提供则使用当前日期
        reference_date = date or datetime.now().strftime("%Y-%m-%d")
        save_sales_records(data["data"], "meituan", reference_date)
        
        # 更新任务状态
        update_task_status(task_id, "completed", 100, result=data)
        
        return {"status": "success", "data": data}
    except Exception as e:
        logger.error(f"获取美团数据失败: {str(e)}")
        update_task_status(task_id, "failed", 0, error=str(e))
        return {"status": "error", "error": str(e)}


@celery_app.task(bind=True)
def fetch_duowei_task(self, task_id: int, date: str = None):
    """获取多维数据的后台任务"""
    # 确保在函数内部可以访问datetime
    from datetime import datetime
    
    try:
        # 检查任务是否存在，如果不存在则提前返回
        if not update_task_status(task_id, "running", 10):
            logger.error(f"任务不存在: Task with id {task_id} not found")
            return {"status": "error", "error": f"Task with id {task_id} not found"}
        
        # 获取数据
        from services.duowei_service import fetch_duowei_data
        result = fetch_duowei_data(date)
        update_task_status(task_id, "running", 50)
        
        # 检查是否获取成功
        if not result["success"]:
            update_task_status(task_id, "failed", 0, error=result["message"])
            return {"status": "error", "error": result["message"]}
        
        # 保存数据到数据库
        # 使用date作为默认日期，如果未提供则使用当前日期
        reference_date = date or datetime.now().strftime("%Y-%m-%d")
        save_sales_records(result["data"], "duowei", reference_date)
        
        # 更新任务状态
        update_task_status(task_id, "completed", 100, result=result)
        
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"获取多维数据失败: {str(e)}")
        update_task_status(task_id, "failed", 0, error=str(e))
        return {"status": "error", "error": str(e)}


@celery_app.task(bind=True)
def fetch_all_data_task(self, task_id: int, date: str = None):
    """获取所有平台数据的后台任务"""
    # 确保在函数内部可以访问datetime
    from datetime import datetime
    
    try:
        # 检查任务是否存在，如果不存在则提前返回
        if not update_task_status(task_id, "running", 10):
            logger.error(f"任务不存在: Task with id {task_id} not found")
            return {"status": "error", "error": f"Task with id {task_id} not found"}
        
        # 获取任务对象，以便获取用户ID
        from db.crud import get_task
        db = next(get_db())
        task = get_task(db, task_id)
        user_id = task.user_id if task else None
        
        # 获取美团数据
        from services.meituan_service import fetch_meituan_data
        meituan_result = fetch_meituan_data(db, date, user_id)
        update_task_status(task_id, "running", 40)
        
        # 获取多维数据
        from services.duowei_service import fetch_duowei_data
        duowei_result = fetch_duowei_data(date)
        update_task_status(task_id, "running", 70)
        
        # 获取数据列表
        meituan_items = meituan_result.get("data", []) if isinstance(meituan_result, dict) else []
        duowei_items = duowei_result.get("data", []) if isinstance(duowei_result, dict) else []
        
        # 检查数据完整性
        if not meituan_result.get("success", False):
            logger.warning(f"美团数据获取失败: {meituan_result.get('message', '未知错误')}")
        
        if not duowei_result.get("success", False):
            logger.warning(f"多维数据获取失败: {duowei_result.get('message', '未知错误')}")
        
        # 合并数据
        query_date = date or datetime.now().strftime("%Y-%m-%d")
        all_data = {
            "success": meituan_result.get("success", False) or duowei_result.get("success", False),
            "message": "数据获取部分成功" if (meituan_result.get("success", False) or duowei_result.get("success", False)) else "所有数据源获取失败",
            "date": query_date,
            "data": {
                "meituan": {
                    "success": meituan_result.get("success", False),
                    "message": meituan_result.get("message", ""),
                    "data": meituan_items
                },
                "duowei": {
                    "success": duowei_result.get("success", False),
                    "message": duowei_result.get("message", ""),
                    "data": duowei_items
                }
            }
        }
        
        # 保存数据到数据库
        # 使用date作为默认日期，如果未提供则使用当前日期
        reference_date = date or datetime.now().strftime("%Y-%m-%d")
        if meituan_items:
            save_sales_records(meituan_items, "meituan", reference_date)
        if duowei_items:
            save_sales_records(duowei_items, "duowei", reference_date)
        
        # 更新任务状态
        update_task_status(task_id, "completed", 100, result=all_data)
        
        return {"status": "success", "data": all_data}
    except Exception as e:
        logger.error(f"获取所有平台数据失败: {str(e)}")
        update_task_status(task_id, "failed", 0, error=str(e))
        return {"status": "error", "error": str(e)}

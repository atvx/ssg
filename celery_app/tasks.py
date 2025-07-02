import logging
import json
from datetime import datetime, date, timedelta
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
from services.sales_target_service import SalesTargetService

# 配置日志
logger = get_task_logger(__name__)


def clean_stuck_tasks():
    """清理卡住的任务"""
    db = SessionLocal()
    try:
        # 查找所有running状态且超过30分钟未更新的任务
        stuck_tasks = db.query(Task).filter(
            Task.status == "running",
            Task.updated_at < datetime.now() - timedelta(minutes=30)
        ).all()
        
        for task in stuck_tasks:
            logger.warning(f"清理卡住的任务: task_id={task.id}, last_update={task.updated_at}")
            task.status = "failed"
            task.error = "任务执行超时自动清理"
            task.progress = 0
        db.commit()
        return len(stuck_tasks)
    except Exception as e:
        logger.error(f"清理卡住任务失败: {str(e)}")
        return 0
    finally:
        db.close()


def update_task_status(task_id: int, status: str, progress: int, result=None, error=None):
    """更新任务状态，包含超时检查"""
    db = SessionLocal()
    try:
        task = get_task(db, task_id)
        if not task:
            logger.warning(f"尝试更新不存在的任务: Task with id {task_id} not found")
            return False
            
        # 检查任务是否超时
        if task.updated_at and (datetime.now() - task.updated_at).total_seconds() > 1800:  # 30分钟
            logger.warning(f"任务 {task_id} 执行超时")
            task.status = "failed"
            task.error = "任务执行超时"
            task.progress = 0
        else:
            task.status = status
            task.progress = progress
            if result:
                task.result = json.dumps(result, ensure_ascii=False)
            if error:
                task.error = error
            task.updated_at = datetime.now()
        
        db.commit()
        return True
    except Exception as e:
        logger.error(f"更新任务状态失败: {str(e)}")
        return False
    finally:
        db.close()
        logger.debug(f"更新任务状态函数中的数据库连接已关闭 (task_id: {task_id})")


def save_sales_records(records, platform, date_str):
    """保存销售记录到数据库"""
    from datetime import date as date_type
    
    db = SessionLocal()
    try:
        for record in records:
            try:
                sales_record = SalesRecordCreate(
                    date=date_type.fromisoformat(date_str),
                    platform=platform,
                    warehouse_name=record["name"],
                    income_amt=record["incomeAmt"],
                    sales_cart_count=record["salesCartCount"],
                    avg_income_amt=record["avgIncomeAmt"]
                )
                create_or_update_sales_record(db, sales_record)
            except Exception as e:
                logger.error(f"保存单条销售记录失败: {str(e)}, record={record}")
                continue
        db.commit()
    except Exception as e:
        logger.error(f"保存销售记录失败: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
        logger.debug(f"保存销售记录函数中的数据库连接已关闭 (platform: {platform}, date: {date_str})")


@celery_app.task(bind=True, 
                 max_retries=3,
                 default_retry_delay=60,
                 autoretry_for=(Exception,),
                 retry_backoff=True,
                 retry_backoff_max=300,
                 rate_limit='10/m')
def fetch_meituan_task(self, task_id: int, date: str = None, user_id: int = None):
    """获取美团数据的后台任务"""
    logger.info(f"开始执行美团数据获取任务: task_id={task_id}, date={date}, user_id={user_id}")
    
    # 清理可能存在的卡住任务
    cleaned_count = clean_stuck_tasks()
    if cleaned_count > 0:
        logger.info(f"清理了 {cleaned_count} 个卡住的任务")
    
    db = None
    try:
        if not update_task_status(task_id, "running", 10):
            logger.error(f"任务不存在: Task with id {task_id} not found")
            return {"status": "error", "error": f"Task with id {task_id} not found"}
        
        db = SessionLocal()
        task = get_task(db, task_id)
        task_user_id = user_id or (task.user_id if task else None)
        
        logger.info(f"开始获取美团数据: date={date}, user_id={task_user_id}")
        data = fetch_meituan_data(db, date, task_user_id)
        update_task_status(task_id, "running", 50)
        
        if not data["success"]:
            error_msg = f"获取美团数据失败: {data['message']}"
            logger.error(error_msg)
            update_task_status(task_id, "failed", 0, error=error_msg)
            return {"status": "error", "error": error_msg}
        
        reference_date = date or datetime.now().strftime("%Y-%m-%d")
        logger.info(f"开始保存美团数据: date={reference_date}")
        save_sales_records(data["data"], "meituan", reference_date)
        
        try:
            target_result = SalesTargetService.update_monthly_targets(db, reference_date)
            if target_result["success"]:
                logger.info(f"美团任务完成后更新月目标成功: {target_result['message']}")
            else:
                logger.warning(f"美团任务完成后更新月目标失败: {target_result['message']}")
        except Exception as target_error:
            logger.error(f"美团任务完成后更新月目标时出错: {str(target_error)}")
        
        update_task_status(task_id, "completed", 100, result=data)
        logger.info(f"美团数据获取任务完成: task_id={task_id}")
        return {"status": "success", "data": data}
        
    except Exception as e:
        error_msg = f"获取美团数据失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        update_task_status(task_id, "failed", 0, error=error_msg)
        raise self.retry(exc=e)
    finally:
        if db:
            db.close()
            logger.debug(f"美团任务中的数据库连接已关闭 (task_id: {task_id})")


@celery_app.task(bind=True,
                 max_retries=3,
                 default_retry_delay=60,
                 autoretry_for=(Exception,),
                 retry_backoff=True,
                 retry_backoff_max=300,
                 rate_limit='10/m')
def fetch_duowei_task(self, task_id: int, date: str = None, user_id: int = None):
    """获取多维数据的后台任务"""
    logger.info(f"开始执行多维数据获取任务: task_id={task_id}, date={date}, user_id={user_id}")
    
    # 清理可能存在的卡住任务
    cleaned_count = clean_stuck_tasks()
    if cleaned_count > 0:
        logger.info(f"清理了 {cleaned_count} 个卡住的任务")
    
    db = None
    try:
        if not update_task_status(task_id, "running", 10):
            logger.error(f"任务不存在: Task with id {task_id} not found")
            return {"status": "error", "error": f"Task with id {task_id} not found"}
        
        db = SessionLocal()
        logger.info(f"开始获取多维数据: date={date}")
        result = fetch_duowei_data(date, db)
        update_task_status(task_id, "running", 50)
        
        if not result["success"]:
            error_msg = f"获取多维数据失败: {result['message']}"
            logger.error(error_msg)
            update_task_status(task_id, "failed", 0, error=error_msg)
            return {"status": "error", "error": error_msg}
        
        reference_date = date or datetime.now().strftime("%Y-%m-%d")
        logger.info(f"开始保存多维数据: date={reference_date}")
        save_sales_records(result["data"], "duowei", reference_date)
        
        try:
            target_result = SalesTargetService.update_monthly_targets(db, reference_date)
            if target_result["success"]:
                logger.info(f"多维任务完成后更新月目标成功: {target_result['message']}")
            else:
                logger.warning(f"多维任务完成后更新月目标失败: {target_result['message']}")
        except Exception as target_error:
            logger.error(f"多维任务完成后更新月目标时出错: {str(target_error)}")
        
        update_task_status(task_id, "completed", 100, result=result)
        logger.info(f"多维数据获取任务完成: task_id={task_id}")
        return {"status": "success", "data": result}
        
    except Exception as e:
        error_msg = f"获取多维数据失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        update_task_status(task_id, "failed", 0, error=error_msg)
        raise self.retry(exc=e)
    finally:
        if db:
            db.close()
            logger.debug(f"多维任务中的数据库连接已关闭 (task_id: {task_id})")


@celery_app.task(bind=True,
                 max_retries=3,
                 default_retry_delay=60,
                 autoretry_for=(Exception,),
                 retry_backoff=True,
                 retry_backoff_max=300,
                 rate_limit='5/m')
def fetch_all_data_task(self, task_id: int, date: str = None, user_id: int = None):
    """获取所有平台数据的后台任务"""
    logger.info(f"开始执行全平台数据获取任务: task_id={task_id}, date={date}, user_id={user_id}")
    
    # 清理可能存在的卡住任务
    cleaned_count = clean_stuck_tasks()
    if cleaned_count > 0:
        logger.info(f"清理了 {cleaned_count} 个卡住的任务")
    
    db = None
    try:
        if not update_task_status(task_id, "running", 10):
            logger.error(f"任务不存在: Task with id {task_id} not found")
            return {"status": "error", "error": f"Task with id {task_id} not found"}
        
        db = SessionLocal()
        all_data = {
            "success": False,
            "message": "",
            "platforms": {}
        }
        
        # 获取美团数据
        logger.info("开始获取美团数据")
        update_task_status(task_id, "running", 20)
        meituan_result = fetch_meituan_data(db, date, user_id)
        all_data["platforms"]["meituan"] = meituan_result
        
        if meituan_result["success"]:
            logger.info("保存美团数据")
            reference_date = date or datetime.now().strftime("%Y-%m-%d")
            save_sales_records(meituan_result["data"], "meituan", reference_date)
        
        # 获取多维数据
        logger.info("开始获取多维数据")
        update_task_status(task_id, "running", 60)
        duowei_result = fetch_duowei_data(date, db)
        all_data["platforms"]["duowei"] = duowei_result
        
        if duowei_result["success"]:
            logger.info("保存多维数据")
            reference_date = date or datetime.now().strftime("%Y-%m-%d")
            save_sales_records(duowei_result["data"], "duowei", reference_date)
        
        # 更新月度销售目标
        try:
            reference_date = date or datetime.now().strftime("%Y-%m-%d")
            target_result = SalesTargetService.update_monthly_targets(db, reference_date)
            if target_result["success"]:
                logger.info(f"全平台任务完成后更新月目标成功: {target_result['message']}")
                all_data["target_update"] = target_result
            else:
                logger.warning(f"全平台任务完成后更新月目标失败: {target_result['message']}")
                all_data["target_update"] = target_result
        except Exception as target_error:
            logger.error(f"全平台任务完成后更新月目标时出错: {str(target_error)}")
            all_data["target_update"] = {"success": False, "error": str(target_error)}
        
        # 设置总体成功状态
        all_data["success"] = meituan_result.get("success", False) or duowei_result.get("success", False)
        all_data["message"] = "全平台数据获取完成"
        
        update_task_status(task_id, "completed", 100, result=all_data)
        logger.info(f"全平台数据获取任务完成: task_id={task_id}")
        return {"status": "success", "data": all_data}
        
    except Exception as e:
        error_msg = f"获取全平台数据失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        update_task_status(task_id, "failed", 0, error=error_msg)
        raise self.retry(exc=e)
    finally:
        if db:
            db.close()
            logger.debug(f"全平台任务中的数据库连接已关闭 (task_id: {task_id})")

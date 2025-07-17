import logging
import json
from datetime import datetime, date, time as dt_time
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session

from celery import shared_task, Task
from celery_app.celery import celery_app
from db.database import SessionLocal, get_db
from db.crud import update_task, create_or_update_sales_record, get_task, create_task
from db.crud import get_task_schedule_configs, update_last_run_at
from models.task import Task as TaskModel, TaskScheduleConfig
from schemas.sales import SalesRecordCreate
from schemas.task import TaskUpdate, TaskCreate
from services.meituan_service import fetch_meituan_data
from services.duowei_service import fetch_duowei_data
from services.sales_target_service import SalesTargetService
import threading

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
        # 确保关闭数据库连接
        db.close()
        logger.debug(f"更新任务状态函数中的数据库连接已关闭 (task_id: {task_id})")


# 保存销售记录到数据库
def save_sales_records(records, platform, date_str):
    # 确保在函数内部可以访问date
    from datetime import date as date_type
    
    db = SessionLocal()
    try:
        for record in records:
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
        logger.error(f"保存销售记录失败: {str(e)}")
        db.rollback()
        raise e
    finally:
        # 确保关闭数据库连接
        db.close()
        logger.debug(f"保存销售记录函数中的数据库连接已关闭 (platform: {platform}, date: {date_str})")


@celery_app.task(bind=True)
def fetch_meituan_task(self, task_id: int, date: str = None, user_id: int = None):
    """获取美团数据的后台任务"""
    # 确保在函数内部可以访问datetime
    from datetime import datetime
    
    # 创建数据库会话
    db = None
    try:
        # 检查任务是否存在，如果不存在则提前返回
        if not update_task_status(task_id, "running", 10):
            logger.error(f"任务不存在: Task with id {task_id} not found")
            return {"status": "error", "error": f"Task with id {task_id} not found"}
        
        # 使用Meituan服务获取数据
        from services.meituan_service import fetch_meituan_data
        db = SessionLocal()
        
        # 获取任务对象，以便获取用户ID
        from db.crud import get_task
        task = get_task(db, task_id)
        # 如果提供了user_id参数，优先使用它，否则使用任务中的用户ID
        task_user_id = user_id or (task.user_id if task else None)
        
        # 获取美团数据
        data = fetch_meituan_data(db, date, task_user_id)
        update_task_status(task_id, "running", 50)
        
        # 检查是否获取成功
        if not data["success"]:
            # 使用date作为默认日期，如果未提供则使用当前日期
            reference_date = date or datetime.now().strftime("%Y-%m-%d")
            error_result = {
                "success": False,
                "message": "美团数据同步失败",
                "date": reference_date,
                "execution_mode": "async",
                "platforms": {
                    "meituan": {
                        "success": False,
                        "message": data["message"],
                        "platform": "meituan",
                        "data": [],
                        "date": reference_date
                    }
                }
            }
            update_task_status(task_id, "failed", 0, error=data["message"], result=error_result)
            return {"status": "error", "data": error_result}
        
        # 保存数据到数据库
        # 使用date作为默认日期，如果未提供则使用当前日期
        reference_date = date or datetime.now().strftime("%Y-%m-%d")
        save_sales_records(data["data"], "meituan", reference_date)
        
        # 更新月度销售目标
        try:
            target_result = SalesTargetService.update_monthly_targets(db, reference_date)
            if target_result["success"]:
                logger.info(f"美团任务完成后更新月目标成功: {target_result['message']}")
                data["target_update"] = {"success": True, "message": target_result["message"]}
            else:
                logger.warning(f"美团任务完成后更新月目标失败: {target_result['message']}")
                data["target_update"] = {"success": False, "message": target_result["message"]}
        except Exception as target_error:
            logger.error(f"美团任务完成后更新月目标时出错: {str(target_error)}")
            data["target_update"] = {"success": False, "error": str(target_error)}
        
        # 更新任务状态
        update_task_status(task_id, "completed", 100, result=data)
        
        return {"status": "success", "data": data}
    except Exception as e:
        logger.error(f"获取美团数据失败: {str(e)}")
        update_task_status(task_id, "failed", 0, error=str(e))
        return {"status": "error", "error": str(e)}
    finally:
        # 确保关闭数据库连接
        if db:
            db.close()
            logger.debug(f"美团任务中的数据库连接已关闭 (task_id: {task_id})")
        
        # 清理浏览器进程
        try:
            from utils.file_utils import force_kill_processes
            logger.info(f"美团任务 {task_id} 完成，清理浏览器进程...")
            force_kill_processes(['msedge', 'msedgedriver', 'Microsoft Edge'])
            
            # 清理临时用户数据目录
            import shutil
            import os
            edge_user_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "edge_user_data")
            if os.path.exists(edge_user_data_dir):
                # 只清理临时会话目录，保留持久化目录
                temp_dirs = [d for d in os.listdir(edge_user_data_dir) 
                            if (d.startswith("task_") or d.startswith("session_")) 
                            and d != "persistent_session"]
                
                for temp_dir in temp_dirs:
                    try:
                        full_path = os.path.join(edge_user_data_dir, temp_dir)
                        if os.path.isdir(full_path):
                            shutil.rmtree(full_path, ignore_errors=True)
                            logger.debug(f"已清理临时目录: {full_path}")
                    except Exception as clean_error:
                        logger.warning(f"清理临时目录失败: {clean_error}")
                        
                # 确保persistent_session目录存在
                persistent_dir = os.path.join(edge_user_data_dir, "persistent_session")
                os.makedirs(persistent_dir, exist_ok=True)
                logger.debug(f"保留持久化会话目录: {persistent_dir}")
        except Exception as cleanup_error:
            logger.warning(f"清理浏览器进程时出错: {cleanup_error}")
            # 继续执行，不影响任务结果


@celery_app.task(bind=True)
def fetch_duowei_task(self, task_id: int, date: str = None, user_id: int = None):
    """获取多维数据的后台任务"""
    # 确保在函数内部可以访问datetime
    from datetime import datetime
    
    # 创建数据库会话
    db = None
    try:
        # 检查任务是否存在，如果不存在则提前返回
        if not update_task_status(task_id, "running", 10):
            logger.error(f"任务不存在: Task with id {task_id} not found")
            return {"status": "error", "error": f"Task with id {task_id} not found"}
        
        # 获取数据
        from services.duowei_service import fetch_duowei_data
        db = SessionLocal()
        result = fetch_duowei_data(date, db)
        update_task_status(task_id, "running", 50)
        
        # 检查是否获取成功
        if not result["success"]:
            # 使用date作为默认日期，如果未提供则使用当前日期
            reference_date = date or datetime.now().strftime("%Y-%m-%d")
            error_result = {
                "success": False,
                "message": "数据同步失败",
                "date": reference_date,
                "execution_mode": "async",
                "platforms": {
                    "duowei": {
                        "success": False,
                        "message": result["message"],
                        "platform": "duowei",
                        "data": [],
                        "date": reference_date
                    }
                }
            }
            update_task_status(task_id, "failed", 0, error=result["message"], result=error_result)
            return {"status": "error", "data": error_result}
        
        # 保存数据到数据库
        # 使用date作为默认日期，如果未提供则使用当前日期
        reference_date = date or datetime.now().strftime("%Y-%m-%d")
        save_sales_records(result["data"], "duowei", reference_date)
        
        # 更新月度销售目标
        try:
            target_result = SalesTargetService.update_monthly_targets(db, reference_date)
            if target_result["success"]:
                logger.info(f"多维任务完成后更新月目标成功: {target_result['message']}")
            else:
                logger.warning(f"多维任务完成后更新月目标失败: {target_result['message']}")
        except Exception as target_error:
            logger.error(f"多维任务完成后更新月目标时出错: {str(target_error)}")
        
        # 构建成功结果
        success_result = {
            "success": True,
            "message": "全平台数据同步完成",
            "date": reference_date,
            "execution_mode": "async",
            "platforms": {
                "duowei": {
                    "success": True,
                    "message": result["message"],
                    "platform": "duowei",
                    "data": result["data"],
                    "date": reference_date
                }
            }
        }
        
        # 更新任务状态
        update_task_status(task_id, "completed", 100, result=success_result)
        
        return {"status": "success", "data": success_result}
    except Exception as e:
        logger.error(f"获取多维数据失败: {str(e)}")
        update_task_status(task_id, "failed", 0, error=str(e))
        return {"status": "error", "error": str(e)}
    finally:
        # 确保关闭数据库连接
        if db:
            db.close()
            logger.debug(f"多维任务中的数据库连接已关闭 (task_id: {task_id})")


@celery_app.task(bind=True)
def fetch_all_data_task(self, task_id: int, date: str = None, user_id: int = None):
    """获取所有平台数据的后台任务"""
    # 确保在函数内部可以访问datetime
    from datetime import datetime
    
    # 创建数据库会话
    db = None
    try:
        # 检查任务是否存在，如果不存在则提前返回
        if not update_task_status(task_id, "running", 10):
            logger.error(f"任务不存在: Task with id {task_id} not found")
            return {"status": "error", "error": f"Task with id {task_id} not found"}
        
        # 获取任务对象，以便获取用户ID
        from db.crud import get_task
        db = SessionLocal()
        task = get_task(db, task_id)
        # 如果提供了user_id参数，优先使用它，否则使用任务中的用户ID
        task_user_id = user_id or (task.user_id if task else None)
        
        # 获取美团数据
        from services.meituan_service import fetch_meituan_data
        meituan_result = fetch_meituan_data(db, date, task_user_id)
        update_task_status(task_id, "running", 40)
        
        # 获取多维数据
        from services.duowei_service import fetch_duowei_data
        duowei_result = fetch_duowei_data(date, db)
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
        
        # 构建平台结果
        platforms_result = {
            "meituan": {
                "success": meituan_result.get("success", False),
                "message": meituan_result.get("message", ""),
                "platform": "meituan",
                "data": meituan_items,
                "date": query_date
            },
            "duowei": {
                "success": duowei_result.get("success", False),
                "message": duowei_result.get("message", ""),
                "platform": "duowei",
                "data": duowei_items,
                "date": query_date
            }
        }
        
        # 判断整体成功状态
        all_success = all(platform["success"] for platform in platforms_result.values())
        any_success = any(platform["success"] for platform in platforms_result.values())
        
        # 根据成功状态设置消息
        if all_success:
            overall_message = "全平台数据同步完成"
        elif any_success:
            overall_message = "部分平台数据同步完成"
        else:
            overall_message = "数据同步失败"
        
        all_data = {
            "success": all_success,
            "message": overall_message,
            "date": query_date,
            "execution_mode": "async",
            "platforms": platforms_result
        }
        
        # 保存数据到数据库
        # 使用date作为默认日期，如果未提供则使用当前日期
        reference_date = date or datetime.now().strftime("%Y-%m-%d")
        if meituan_items:
            save_sales_records(meituan_items, "meituan", reference_date)
        if duowei_items:
            save_sales_records(duowei_items, "duowei", reference_date)
        
        # 更新月度销售目标
        try:
            target_result = SalesTargetService.update_monthly_targets(db, reference_date)
            if target_result["success"]:
                logger.info(f"全平台任务完成后更新月目标成功: {target_result['message']}")
                all_data["target_update"] = {"success": True, "message": target_result["message"]}
            else:
                logger.warning(f"全平台任务完成后更新月目标失败: {target_result['message']}")
                all_data["target_update"] = {"success": False, "message": target_result["message"]}
        except Exception as target_error:
            logger.error(f"全平台任务完成后更新月目标时出错: {str(target_error)}")
            all_data["target_update"] = {"success": False, "error": str(target_error)}
        
        # 更新任务状态
        update_task_status(task_id, "completed", 100, result=all_data)
        
        return {"status": "success", "data": all_data}
    except Exception as e:
        logger.error(f"获取全平台数据失败: {str(e)}")
        update_task_status(task_id, "failed", 0, error=str(e))
        return {"status": "error", "error": str(e)}
    finally:
        # 确保关闭数据库连接
        if db:
            db.close() 
            logger.debug(f"全平台任务中的数据库连接已关闭 (task_id: {task_id})")
        
        # 清理浏览器进程
        try:
            from utils.file_utils import force_kill_processes
            logger.info(f"任务 {task_id} 完成，清理浏览器进程...")
            force_kill_processes(['msedge', 'msedgedriver', 'Microsoft Edge'])
            
            # 清理临时用户数据目录
            import shutil
            import os
            edge_user_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "edge_user_data")
            if os.path.exists(edge_user_data_dir):
                # 只清理临时会话目录，保留持久化目录
                temp_dirs = [d for d in os.listdir(edge_user_data_dir) 
                            if (d.startswith("task_") or d.startswith("session_")) 
                            and d != "persistent_session"]
                
                for temp_dir in temp_dirs:
                    try:
                        full_path = os.path.join(edge_user_data_dir, temp_dir)
                        if os.path.isdir(full_path):
                            shutil.rmtree(full_path, ignore_errors=True)
                            logger.debug(f"已清理临时目录: {full_path}")
                    except Exception as clean_error:
                        logger.warning(f"清理临时目录失败: {clean_error}")
                        
                # 确保persistent_session目录存在
                persistent_dir = os.path.join(edge_user_data_dir, "persistent_session")
                os.makedirs(persistent_dir, exist_ok=True)
                logger.debug(f"保留持久化会话目录: {persistent_dir}")
        except Exception as cleanup_error:
            logger.warning(f"清理浏览器进程时出错: {cleanup_error}")
            # 继续执行，不影响任务结果


# 新增定时任务，从数据库读取配置
@celery_app.task
def auto_sync_data():
    """
    自动同步数据的定时任务，根据数据库中的配置动态调整同步频率
    """
    logger.info("开始执行自动数据同步定时任务")
    
    # 获取当前时间
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    
    # 记录当前时间信息，便于调试
    current_minute = now.minute
    current_hour = now.hour
    current_day_of_week = now.weekday()
    current_day_of_month = now.day
    current_month = now.month
    
    logger.info(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}, 分钟: {current_minute}, 小时: {current_hour}, 星期: {current_day_of_week}, 日: {current_day_of_month}, 月: {current_month}")
    
    # 创建数据库会话
    db = SessionLocal()
    try:
        # 获取所有启用的调度配置
        enabled_configs = get_task_schedule_configs(db, enabled=True)
        
        if not enabled_configs:
            logger.info("没有找到启用的调度配置，跳过执行")
            return {"status": "skipped", "message": "No enabled schedule configs found"}
        
        logger.info(f"找到 {len(enabled_configs)} 个启用的调度配置")
        for idx, config in enumerate(enabled_configs):
            logger.info(f"配置 {idx+1}: ID={config.id}, 名称='{config.name}', 类型={config.schedule_type}, 任务={config.task_type}, 上次执行={config.last_run_at}")
            if config.schedule_type == "crontab":
                logger.info(f"  Crontab配置: 分钟={config.minute}, 小时={config.hour}, 星期={config.day_of_week}, 日={config.day_of_month}, 月={config.month_of_year}")
            elif config.schedule_type == "interval":
                logger.info(f"  Interval配置: 间隔={config.interval_seconds}秒")
            if config.start_time and config.end_time:
                logger.info(f"  时间段限制: {config.start_time} - {config.end_time}")
        
        executed_tasks = []
        
        # 遍历所有配置，检查是否需要执行
        for config in enabled_configs:
            # 检查时间段限制
            should_execute = True
            
            # 如果配置了时间段，检查当前时间是否在时间段内
            if config.start_time and config.end_time:
                if config.start_time <= current_time <= config.end_time:
                    logger.info(f"配置 '{config.name}' 在时间段 {config.start_time}-{config.end_time} 内，允许执行")
                else:
                    logger.info(f"配置 '{config.name}' 不在时间段 {config.start_time}-{config.end_time} 内，跳过执行")
                    should_execute = False
            
            # 根据调度类型检查是否应该执行
            if should_execute and config.schedule_type == "crontab":
                from celery.schedules import crontab
                
                # 处理分钟匹配
                minute_match = False
                if config.minute == "*":
                    minute_match = True
                    logger.info(f"分钟通配符匹配: 当前分钟 {current_minute}, 配置为 '*', 匹配成功")
                elif "," in config.minute:
                    # 处理逗号分隔的值
                    minute_values = config.minute.split(",")
                    # 将字符串转换为整数进行比较
                    try:
                        minute_values_int = [int(m.strip()) for m in minute_values]
                        minute_match = current_minute in minute_values_int
                        logger.info(f"分钟列表匹配: 当前分钟 {current_minute}, 分钟列表 {minute_values_int}, 匹配结果: {minute_match}")
                        
                        # 添加更详细的日志，记录每一步判断
                        if not minute_match:
                            logger.info(f"当前分钟 {current_minute} 不在列表 {minute_values_int} 中")
                        else:
                            logger.info(f"当前分钟 {current_minute} 在列表 {minute_values_int} 中，匹配成功")
                    except ValueError as e:
                        # 如果转换失败，回退到字符串比较
                        logger.warning(f"分钟值转换失败: {str(e)}，使用字符串比较")
                        minute_match = str(current_minute) in minute_values
                        logger.warning(f"字符串比较结果: 当前分钟 {current_minute}, 分钟列表 {minute_values}, 匹配结果: {minute_match}")
                elif "/" in config.minute:
                    # 处理 */n 格式
                    parts = config.minute.split("/")
                    if len(parts) == 2 and parts[0] == "*":
                        try:
                            interval = int(parts[1])
                            # 生成所有有效的分钟值
                            valid_minutes = [i for i in range(0, 60, interval)]
                            # 直接检查当前分钟是否在有效分钟列表中
                            minute_match = current_minute in valid_minutes
                            
                            # 添加更详细的日志，记录每一步判断
                            logger.info(f"分钟间隔匹配详情: 当前分钟 {current_minute}, 间隔 {interval}")
                            logger.info(f"有效分钟列表: {valid_minutes}")
                            logger.info(f"当前分钟 {current_minute} {'在' if minute_match else '不在'} 有效分钟列表中")
                            logger.info(f"最终匹配结果: {minute_match}")
                            
                            # 确保0和5的倍数能正确匹配
                            if current_minute % interval == 0 and not minute_match:
                                logger.warning(f"检测到异常: 当前分钟 {current_minute} 应该匹配间隔 {interval}，但未匹配成功，强制设置为匹配")
                                minute_match = True
                        except ValueError as e:
                            logger.error(f"解析分钟间隔出错: {str(e)}")
                            minute_match = False
                else:
                    # 处理单个值
                    try:
                        minute_match = current_minute == int(config.minute)
                        logger.info(f"分钟单值匹配: 当前分钟 {current_minute}, 配置值 {config.minute}, 匹配结果: {minute_match}")
                    except ValueError:
                        minute_match = False
                
                # 处理小时匹配
                hour_match = False
                if config.hour == "*":
                    hour_match = True
                    logger.info(f"小时通配符匹配: 当前小时 {current_hour}, 配置为 '*', 匹配成功")
                elif "," in config.hour:
                    # 处理逗号分隔的值
                    hour_values = config.hour.split(",")
                    try:
                        hour_values_int = [int(h.strip()) for h in hour_values]
                        hour_match = current_hour in hour_values_int
                        logger.info(f"小时列表匹配: 当前小时 {current_hour}, 小时列表 {hour_values_int}, 匹配结果: {hour_match}")
                    except ValueError:
                        # 如果转换失败，回退到字符串比较
                        hour_match = str(current_hour) in hour_values
                        logger.info(f"小时字符串列表匹配: 当前小时 {current_hour}, 小时列表 {hour_values}, 匹配结果: {hour_match}")
                elif "-" in config.hour:
                    # 处理范围值，如 "6-11"
                    try:
                        start_hour, end_hour = map(int, config.hour.split("-"))
                        hour_match = start_hour <= current_hour <= end_hour
                        logger.info(f"小时范围匹配: 当前小时 {current_hour}, 范围 {start_hour}-{end_hour}, 匹配结果: {hour_match}")
                    except ValueError:
                        hour_match = False
                else:
                    # 处理单个值
                    try:
                        hour_match = current_hour == int(config.hour)
                        logger.info(f"小时单值匹配: 当前小时 {current_hour}, 配置值 {config.hour}, 匹配结果: {hour_match}")
                    except ValueError:
                        hour_match = False
                
                # 简化处理日期、星期和月份匹配，默认匹配所有
                day_of_week_match = config.day_of_week == "*"
                day_of_month_match = config.day_of_month == "*"
                month_of_year_match = config.month_of_year == "*"
                
                # 记录其他时间字段匹配情况
                logger.info(f"其他时间字段匹配: 星期({day_of_week_match}), 日期({day_of_month_match}), 月份({month_of_year_match})")
                
                # 最终匹配结果
                crontab_match = minute_match and hour_match and day_of_week_match and day_of_month_match and month_of_year_match
                
                if not crontab_match:
                    logger.info(f"配置 '{config.name}' 的crontab表达式不匹配当前时间，跳过执行")
                    logger.info(f"匹配详情: 分钟({minute_match}), 小时({hour_match}), 星期({day_of_week_match}), 日期({day_of_month_match}), 月份({month_of_year_match})")
                    should_execute = False
                else:
                    logger.info(f"配置 '{config.name}' 的crontab表达式匹配当前时间，准备执行")
            
            elif should_execute and config.schedule_type == "interval":
                # 对于interval类型，检查上次执行时间是否已经过了指定的间隔
                if config.last_run_at:
                    elapsed_seconds = (now - config.last_run_at).total_seconds()
                    if elapsed_seconds < config.interval_seconds:
                        logger.info(f"配置 '{config.name}' 的间隔时间未到，上次执行: {config.last_run_at}，间隔: {config.interval_seconds}秒，已过: {elapsed_seconds}秒，跳过执行")
                        should_execute = False
                    else:
                        logger.info(f"配置 '{config.name}' 的间隔时间已到，上次执行: {config.last_run_at}，间隔: {config.interval_seconds}秒，已过: {elapsed_seconds}秒，准备执行")
                else:
                    logger.info(f"配置 '{config.name}' 首次执行，无上次执行时间记录")
            
            # 如果通过了所有检查，执行任务
            if should_execute:
                logger.info(f"执行调度配置 '{config.name}' (ID: {config.id})")
                
                # 创建任务记录
                task_params = {
                    "date": current_date,
                    "platform": "all" if config.task_type == "fetch_all" else config.task_type.replace("fetch_", ""),
                    "auto_sync": True,
                    "schedule_config_id": config.id,
                    "schedule_type": config.schedule_type  # 添加调度类型，以便任务执行时知道是否需要更新last_run_at
                }
                
                # 获取系统管理员用户（假设ID为1是超级管理员）
                admin_id = 1
                
                # 创建任务记录
                task = create_task(db, TaskCreate(
                    task_type=config.task_type, 
                    params=task_params
                ), admin_id)
                
                # 根据任务类型执行相应的任务
                if config.task_type == "fetch_meituan":
                    logger.info(f"执行美团数据同步任务，配置: {config.name}")
                    fetch_meituan_task.delay(task.id, current_date, admin_id)
                elif config.task_type == "fetch_duowei":
                    logger.info(f"执行多维数据同步任务，配置: {config.name}")
                    fetch_duowei_task.delay(task.id, current_date, admin_id)
                elif config.task_type == "fetch_all":
                    logger.info(f"执行全平台数据同步任务，配置: {config.name}")
                    fetch_all_data_task.delay(task.id, current_date, admin_id)
                else:
                    logger.warning(f"未知的任务类型: {config.task_type}，配置: {config.name}")
                    continue
                
                # 更新最后执行时间 - 只更新interval类型的配置
                # 对于crontab类型的配置，不更新last_run_at，让它在每个匹配的时间点都执行
                if config.schedule_type == "interval":
                    update_last_run_at(db, config.id)
                    logger.info(f"已更新interval类型配置 '{config.name}' 的最后执行时间")
                else:
                    # 对于crontab类型，记录执行但不更新last_run_at
                    logger.info(f"crontab类型配置 '{config.name}' 不更新最后执行时间，将在下一个匹配时间点再次执行")
                    # 确保数据库中的last_run_at为空，以防之前被错误设置
                    if config.last_run_at is not None:
                        from db.crud import update_task_schedule_config
                        from schemas.task import TaskScheduleConfigUpdate
                        update_task_schedule_config(db, config.id, TaskScheduleConfigUpdate(last_run_at=None))
                        logger.warning(f"检测到crontab类型配置 '{config.name}' 的last_run_at不为空，已重置为空")
                
                executed_tasks.append({
                    "config_id": config.id,
                    "config_name": config.name,
                    "task_id": task.id,
                    "task_type": config.task_type,
                    "executed_at": now.isoformat()
                })
        
        if executed_tasks:
            logger.info(f"成功执行了 {len(executed_tasks)} 个调度任务")
            return {
                "status": "success", 
                "message": f"成功执行了 {len(executed_tasks)} 个调度任务",
                "executed_tasks": executed_tasks
            }
        else:
            logger.info("没有找到需要执行的调度任务")
            return {
                "status": "skipped", 
                "message": "No tasks to execute at this time"
            }
    except Exception as e:
        logger.error(f"执行自动数据同步定时任务失败: {str(e)}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return {"status": "error", "error": str(e)}
    finally:
        # 确保关闭数据库连接
        db.close()
        logger.debug("自动同步任务中的数据库连接已关闭")


# 启动定时任务的线程函数
def start_scheduled_tasks():
    """
    启动定时任务的线程函数，设置Celery Beat调度
    """
    from celery.schedules import crontab
    
    logger.info("正在启动定时任务调度器...")
    
    # 设置默认的调度，每分钟执行一次auto_sync_data任务
    # auto_sync_data任务会检查数据库中的配置，决定是否需要执行具体的同步任务
    celery_app.conf.beat_schedule = {
        'check_schedule_configs_every_minute': {
            'task': 'celery_app.tasks.auto_sync_data',
            'schedule': crontab(minute='*'),  # 每分钟执行一次
            'options': {'expires': 50}  # 任务过期时间50秒
        }
    }
    
    logger.info("定时任务调度器已启动，将每分钟检查一次调度配置")


# 在应用启动时自动启动定时任务线程
def init_scheduled_tasks():
    """
    初始化定时任务，在应用启动时调用
    """
    # 创建并启动线程
    scheduler_thread = threading.Thread(target=start_scheduled_tasks, daemon=True)
    scheduler_thread.start()
    logger.info("定时任务初始化线程已启动")


# 初始化默认的调度配置
def init_default_schedule_configs():
    """
    初始化默认的调度配置，如果数据库中没有配置，则创建默认配置
    """
    from schemas.task import TaskScheduleConfigCreate
    
    db = SessionLocal()
    try:
        # 检查是否已有配置
        existing_configs = get_task_schedule_configs(db)
        if existing_configs:
            logger.info(f"已存在 {len(existing_configs)} 个调度配置，跳过创建默认配置")
            return
        
        # 创建上午配置（每半小时执行一次）
        morning_config = TaskScheduleConfigCreate(
            name="上午数据同步",
            description="上午6:00-12:00每半小时同步一次全平台数据",
            task_type="fetch_all",
            schedule_type="crontab",
            minute="0,30",  # 每小时的0分和30分
            hour="6-11",    # 6点到11点
            start_time="06:00:00",
            end_time="12:00:00",
            enabled=True
        )
        
        # 创建下午配置（每5分钟执行一次）
        afternoon_config = TaskScheduleConfigCreate(
            name="下午数据同步",
            description="下午12:00-23:59每5分钟同步一次全平台数据",
            task_type="fetch_all",
            schedule_type="crontab",
            minute="*/5",  # 每5分钟执行一次
            hour="12-23",  # 12点到23点
            start_time="12:00:00",
            end_time="23:59:59",
            enabled=True
        )
        
        # 创建默认配置
        from db.crud import create_task_schedule_config
        create_task_schedule_config(db, morning_config)
        create_task_schedule_config(db, afternoon_config)
        
        logger.info("成功创建默认调度配置")
    except Exception as e:
        logger.error(f"创建默认调度配置失败: {str(e)}")
    finally:
        db.close()


# 在模块加载时初始化定时任务
init_scheduled_tasks()

# 在模块加载时初始化默认调度配置
init_default_schedule_configs()

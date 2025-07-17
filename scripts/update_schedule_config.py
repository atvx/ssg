#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
更新现有的调度配置
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.database import SessionLocal
from db.crud import get_task_schedule_config_by_name, update_task_schedule_config
from schemas.task import TaskScheduleConfigUpdate

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_schedule_configs():
    """更新调度配置"""
    db = SessionLocal()
    try:
        # 更新下午数据同步配置
        afternoon_config = get_task_schedule_config_by_name(db, "下午数据同步")
        if afternoon_config:
            # 检查当前配置
            logger.info(f"当前下午数据同步配置: minute={afternoon_config.minute}, hour={afternoon_config.hour}")
            
            # 根据当前配置选择合适的更新策略
            if "," in afternoon_config.minute:
                # 已经是列表格式，确保格式正确
                update_data = TaskScheduleConfigUpdate(
                    description="下午12:00-23:59每5分钟同步一次全平台数据",
                    minute="0,5,10,15,20,25,30,35,40,45,50,55",  # 确保格式正确
                    hour="12-23",
                    start_time="12:00:00",
                    end_time="23:59:59",
                    enabled=True
                )
            else:
                # 使用*/5格式
                update_data = TaskScheduleConfigUpdate(
                    description="下午12:00-23:59每5分钟同步一次全平台数据",
                    minute="*/5",  # 使用*/5格式
                    hour="12-23",
                    start_time="12:00:00",
                    end_time="23:59:59",
                    enabled=True
                )
            
            updated_config = update_task_schedule_config(db, afternoon_config.id, update_data)
            if updated_config:
                logger.info(f"成功更新下午数据同步配置: {updated_config.name}, minute={updated_config.minute}")
            else:
                logger.error("更新下午数据同步配置失败")
        else:
            logger.warning("未找到下午数据同步配置")
            
        # 更新上午数据同步配置
        morning_config = get_task_schedule_config_by_name(db, "上午数据同步")
        if morning_config:
            # 检查当前配置
            logger.info(f"当前上午数据同步配置: minute={morning_config.minute}, hour={morning_config.hour}")
            
            # 根据当前配置选择合适的更新策略
            if "," in morning_config.minute:
                # 已经是列表格式，确保格式正确
                update_data = TaskScheduleConfigUpdate(
                    description="上午6:00-12:00每5分钟同步一次全平台数据",
                    minute="0,5,10,15,20,25,30,35,40,45,50,55",  # 确保格式正确
                    hour="6-11",
                    start_time="06:00:00",
                    end_time="12:00:00",
                    enabled=True
                )
            else:
                # 使用*/5格式
                update_data = TaskScheduleConfigUpdate(
                    description="上午6:00-12:00每5分钟同步一次全平台数据",
                    minute="*/5",  # 使用*/5格式
                    hour="6-11",
                    start_time="06:00:00",
                    end_time="12:00:00",
                    enabled=True
                )
            
            updated_config = update_task_schedule_config(db, morning_config.id, update_data)
            if updated_config:
                logger.info(f"成功更新上午数据同步配置: {updated_config.name}, minute={updated_config.minute}")
            else:
                logger.error("更新上午数据同步配置失败")
        else:
            logger.warning("未找到上午数据同步配置")
            
    except Exception as e:
        logger.error(f"更新调度配置失败: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("开始更新调度配置...")
    update_schedule_configs()
    logger.info("调度配置更新完成") 
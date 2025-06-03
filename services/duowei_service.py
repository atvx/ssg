import json
import logging
from typing import List, Optional, Dict, Any
import datetime
import requests
from fastapi import HTTPException, status

from core.duowei.data import get_all_duowei_data
from config.settings import settings

# 配置日志
logger = logging.getLogger(__name__)


def fetch_duowei_data(date: Optional[str] = None) -> Dict[str, Any]:
    """
    获取多维系统销售数据
    
    Args:
        date: 查询日期（格式为YYYY-MM-DD），为空时默认为当天
    
    Returns:
        Dict[str, Any]: 销售数据，格式为：
        {
            "success": true,
            "message": "获取数据成功",
            "date": "2025-05-19",
            "platform": "duowei",
            "data": [
                {
                    "incomeAmt": 2053.5,
                    "salesCartCount": 8,
                    "avgIncomeAmt": 256.69,
                    "name": "昆明龙泉仓"
                },
                ...
            ]
        }
    """
    # 初始化结果
    result = {
        "success": False,
        "message": "",
        "platform": "duowei",
        "data": []
    }
    
    # 处理日期参数
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # 默认使用今天作为查询日期
    target_date = date if date else today
    
    # 将日期信息添加到结果中
    result["date"] = target_date
    
    logger.info(f"开始获取多维系统数据，日期: {target_date}")
    
    try:
        # 获取多维系统配置
        duowei_config = settings.DUOWEI_CONFIG if hasattr(settings, "DUOWEI_CONFIG") else {}
        
        # 确保所有必要的配置都存在
        base_url = duowei_config.get("BASE_URL")
        user_id = duowei_config.get("USER_ID")
        db_name = duowei_config.get("DB_NAME")
            
        # 创建精简的配置字典，只包含必要的配置项
        config = {
            "BASE_URL": base_url,
            "USER_ID": user_id,
            "DB_NAME": db_name,
        }
        
        logger.info(f"多维系统配置准备完成: BASE_URL={base_url}, USER_ID={user_id}, DB_NAME={db_name}")
        
        # 验证必要的配置
        missing_configs = []
        for key in ["BASE_URL", "USER_ID", "DB_NAME"]:
            if not config.get(key):
                missing_configs.append(key)
        
        if missing_configs:
            error_msg = f"多维系统配置错误: {', '.join(missing_configs)} 未设置"
            logger.error(error_msg)
            result["message"] = error_msg
            return result
        
        # 调用多维系统API获取数据
        try:
            logger.info("正在调用多维系统API获取数据")
            data = get_all_duowei_data(config, target_date)
            logger.info(f"成功获取多维系统数据，共 {len(data)} 条记录")
            
            # 更新结果
            result["success"] = True
            result["message"] = "获取数据成功"
            result["data"] = data
            
            return result
        except requests.RequestException as e:
            logger.error(f"多维系统API请求失败: {str(e)}")
            result["message"] = f"多维系统API请求失败: {str(e)}"
            return result
        except Exception as e:
            logger.error(f"获取多维系统数据失败: {str(e)}")
            result["message"] = f"获取多维系统数据失败: {str(e)}"
            return result
            
    except Exception as e:
        logger.error(f"获取多维系统数据过程中发生未知错误: {str(e)}")
        result["message"] = f"获取多维系统数据过程中发生未知错误: {str(e)}"
        return result

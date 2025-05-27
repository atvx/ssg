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
        config = {
            "BASE_URL": settings.DUOWEI_CONFIG["BASE_URL"],
            "USER_ID": settings.DUOWEI_CONFIG["USER_ID"],
            "DB_NAME": settings.DUOWEI_CONFIG["DB_NAME"],
            "OUTPUT_FILE": "sales_duowei.json",
            "SAVE_TO_FILE": False  # 默认不保存结果到文件
        }
        
        # 验证配置
        for key, value in config.items():
            if not value and key != "OUTPUT_FILE":
                logger.error(f"多维系统配置错误: {key} 未设置")
                result["message"] = f"多维系统配置错误: {key} 未设置"
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

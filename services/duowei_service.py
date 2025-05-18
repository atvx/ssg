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


def fetch_duowei_data(date_str: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    获取多维系统销售数据
    
    Args:
        date_str: 日期字符串，格式为YYYY-MM-DD，不传则默认获取今天
    
    Returns:
        List[Dict]: 销售数据列表
        
    Raises:
        HTTPException: 当获取数据失败时
    """
    if not date_str:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"开始获取多维系统数据，日期: {date_str}")
    
    try:
        # 获取多维系统配置
        config = {
            "BASE_URL": settings.DUOWEI_CONFIG["BASE_URL"],
            "USER_ID": settings.DUOWEI_CONFIG["USER_ID"],
            "DB_NAME": settings.DUOWEI_CONFIG["DB_NAME"],
            "OUTPUT_FILE": "sales_duowei.json"
        }
        
        # 验证配置
        for key, value in config.items():
            if not value and key != "OUTPUT_FILE":
                logger.error(f"多维系统配置错误: {key} 未设置")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"msg": "多维系统配置不完整", "error_type": "config_error", "field": key}
                )
        
        # 调用多维系统API获取数据
        try:
            logger.info("正在调用多维系统API获取数据")
            data = get_all_duowei_data(config, date_str)
            logger.info(f"成功获取多维系统数据，共 {len(data)} 条记录")
            return data
        except requests.RequestException as e:
            logger.error(f"多维系统API请求失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"msg": "无法连接到多维系统API", "error_type": "api_connection_error"}
            )
        except Exception as e:
            logger.error(f"获取多维系统数据失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"msg": "获取多维系统数据失败", "error_type": "data_fetch_error"}
            )
            
    except HTTPException:
        # 直接传递HTTP异常
        raise
    except Exception as e:
        logger.error(f"获取多维系统数据过程中发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"msg": "获取多维系统数据失败", "error_type": "unknown_error"}
        )

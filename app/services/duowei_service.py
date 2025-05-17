import json
from typing import List, Optional, Dict, Any
import datetime
import requests

from app.core.duowei.data import get_all_duowei_data
from app.config.settings import settings


def fetch_duowei_data(date_str: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    获取多维系统销售数据
    
    Args:
        date_str: 日期字符串，格式为YYYY-MM-DD，不传则默认获取今天
    
    Returns:
        List[Dict]: 销售数据列表
    """
    if not date_str:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # 获取多维系统配置
    config = {
        "BASE_URL": settings.DUOWEI_CONFIG["BASE_URL"],
        "USER_ID": settings.DUOWEI_CONFIG["USER_ID"],
        "DB_NAME": settings.DUOWEI_CONFIG["DB_NAME"],
        "OUTPUT_FILE": "sales_duowei.json"
    }
    
    # 调用多维系统API获取数据
    data = get_all_duowei_data(config, date_str)
    
    return data

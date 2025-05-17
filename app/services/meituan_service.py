import json
from typing import List, Optional, Dict, Any
import datetime

from app.core.meituan.auth import login_with_phone, login_with_account
from app.core.meituan.browser import init_chrome_driver
from app.core.meituan.navigation import navigate_to_business_overview
from app.core.meituan.data import get_all_meituan_data

from app.config.settings import settings
from app.services.browser_service import get_browser


def fetch_meituan_data(date_str: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    获取美团POS系统销售数据
    
    Args:
        date_str: 日期字符串，格式为YYYY-MM-DD，不传则默认获取今天
    
    Returns:
        List[Dict]: 销售数据列表
    """
    if not date_str:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # 初始化浏览器
    browser = get_browser()
    
    try:
        # 登录美团
        if settings.LOGIN_MODE == 0:  # 手机号登录
            login_with_phone(
                browser, 
                settings.MEITUAN_CONFIG["LOGIN_URL"],
                settings.MEITUAN_CONFIG["PHONE_NUMBER"]
            )
        else:  # 账号登录
            login_with_account(
                browser,
                settings.MEITUAN_CONFIG["LOGIN_URL"],
                settings.ACCOUNT_CONFIG["USERNAME"],
                settings.ACCOUNT_CONFIG["PASSWORD"]
            )
        
        # 导航到业务概览页面
        navigate_to_business_overview(browser, settings.MEITUAN_CONFIG["BUSINESS_OVERVIEW_URL"])
        
        # 选择目标组织
        target_org = settings.MEITUAN_CONFIG["TARGET_ORG"]
        
        # 获取所有门店数据
        shop_data = get_all_meituan_data(browser, None, {
            "OUTPUT_FILE": "sales_meituan.json",
            "API_TIMEOUT": 30
        }, date_str)
        
        return shop_data
    
    finally:
        # 关闭浏览器
        if browser:
            browser.quit()


def verify_meituan_auth(code: str, task_id: str) -> bool:
    """验证美团登录验证码"""
    # TODO: 实现验证码验证功能
    return True

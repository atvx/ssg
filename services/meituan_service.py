import json
import logging
from typing import List, Optional, Dict, Any
import datetime
from fastapi import HTTPException, status
from selenium.webdriver.support.ui import WebDriverWait
import time
import os
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
import traceback
from urllib.parse import urlencode, quote

from core.meituan.auth import login_with_phone, login_with_account, select_organization, check_login, choose_organization
from core.meituan.browser import init_chrome_driver
from core.meituan.navigation import navigate_to_business_overview, navigate_to_report_center
from core.meituan.data import get_all_meituan_data
from utils.browser_utils import hide_all_popups, handle_iframe_slider, monitor_api_response

from config.settings import settings
from services.browser_service import get_browser
from celery import shared_task
from sqlalchemy.orm import Session
from utils.redis_utils import VerificationManager
from db.database import get_db

# 配置日志
logger = logging.getLogger(__name__)

# 定义常量
LOGIN_URL = settings.MEITUAN_CONFIG["LOGIN_URL"]
REPORT_CENTER_URL = settings.MEITUAN_CONFIG["BUSINESS_OVERVIEW_URL"]


@shared_task(bind=True, max_retries=3)
def fetch_meituan_data_task(self):
    """Celery异步任务：获取美团数据"""
    try:
        db = next(get_db())
        task_data = fetch_meituan_data(db)
        return task_data
    except Exception as e:
        logger.error(f"获取美团数据失败: {e}")
        logger.error(traceback.format_exc())
        # 重试，退避策略: 5分钟, 10分钟, 15分钟
        retry_countdown = (self.request.retries + 1) * 300
        self.retry(exc=e, countdown=retry_countdown)


def fetch_meituan_data(db: Session) -> Dict[str, Any]:
    """获取美团POS销售数据
    
    Args:
        db: 数据库会话
        
    Returns:
        Dict[str, Any]: 提取的数据
    """
    driver = None
    task_result = {
        "success": False,
        "message": "",
        "data": None,
        "verification_task_id": None,
        "verification_needed": False
    }
    
    try:
        # 初始化浏览器，开启API监控
        # 创建一个包含所有参数的配置字典
        browser_config = {
            "USER_DATA_DIR": settings.CHROME_USER_DATA_DIR,
            "HEADLESS": False,
            "MONITOR_API_RESPONSE": True,
            "MONITOR_SCOPES": [".*pos\.meituan\.com.*"]  # 匹配所有美团POS域名下的请求
        }
        
        # 使用配置字典初始化浏览器
        driver = init_chrome_driver(config=browser_config)
        
        # 检查是否已登录
        driver.get(LOGIN_URL)
        logger.info("正在检查登录状态...")
        login_status = check_login(driver)
        
        if not login_status:
            logger.info("未登录，正在尝试登录...")
            # 创建WebDriverWait对象
            wait = WebDriverWait(driver, 10)
            login_success = login_with_account(
                driver, 
                wait,
                "cookies_meituan.json"
            )
            
            if not login_success:
                logger.error("登录失败")
                task_result["message"] = "登录失败，请检查账号密码或登录环境"
                return task_result
        else:
            logger.info("已登录")
        
        # 选择机构
        wait = WebDriverWait(driver, 10)
        target_org = settings.MEITUAN_CONFIG["TARGET_ORG"]
        org_success = choose_organization(driver, wait, target_org)
        if not org_success:
            logger.error("选择机构失败")
            task_result["message"] = "选择机构失败"
            return task_result
        
        # 进入数据中心
        logger.info("正在进入报表中心...")
        try:
            # 改进导航逻辑
            # 1. 先导航到报表中心
            navigate_success = navigate_to_report_center(driver, wait)
            if not navigate_success:
                logger.warning("导航到报表中心失败，尝试直接导航到业务概览页面")
                
            # 2. 然后导航到业务概览页面
            logger.info(f"导航到业务概览页面: {settings.MEITUAN_CONFIG['BUSINESS_OVERVIEW_URL']}")
            driver.get(settings.MEITUAN_CONFIG["BUSINESS_OVERVIEW_URL"])
            time.sleep(5)  # 增加等待时间确保页面加载完成
            
            # 3. 检查URL确认是否成功导航
            logger.info(f"当前URL: {driver.current_url}")
            if "business" in driver.current_url:
                logger.info("成功导航到业务概览页面")
                # 隐藏弹窗
                hide_all_popups(driver)
            else:
                logger.error("导航到业务概览页面失败")
                task_result["message"] = "无法导航到业务概览页面"
                return task_result
        except Exception as e:
            logger.error(f"导航到业务概览页面时出错: {e}")
            task_result["message"] = f"导航失败: {str(e)}"
            return task_result
            
        # 等待页面加载完成
        time.sleep(5)  # 增加等待时间
        
        # 从API获取仓库列表
        logger.info("获取仓库列表...")
        
        # 清除之前的请求记录
        if hasattr(driver, 'requests'):
            driver.requests.clear()
        
        # 在页面上触发API请求
        logger.info("正在导航到报表中心，触发API请求...")
        driver.get(settings.MEITUAN_CONFIG["BUSINESS_OVERVIEW_URL"])
        time.sleep(5)  # 等待页面加载和API请求发送
        
        # 使用selenium-wire监控API响应
        warehouse_response = monitor_api_response(
            driver,
            "/tree/paged/query",  # URL匹配模式
            timeout=60,  # 超时时间
            methods=['POST']
        )
        
        if not warehouse_response:
            logger.warning("未通过tree/paged/query路径获取到仓库列表，尝试备用URL模式")
            # 尝试备用API模式
            warehouse_response = monitor_api_response(
                driver,
                "warehouse",  # 尝试包含warehouse的URL
                timeout=30,
                methods=['POST', 'GET']
            )
            
        if not warehouse_response:
            logger.error("获取仓库列表失败")
            task_result["message"] = "获取仓库列表失败，无法获取报表数据"
            return task_result
            
        logger.info(f"获取到仓库列表响应")
        
        # 处理仓库数据
        warehouses = extract_warehouses(warehouse_response)
        if not warehouses:
            logger.error("未找到任何仓库")
            task_result["message"] = "API响应中未找到仓库数据"
            return task_result
            
        logger.info(f"成功提取 {len(warehouses)} 个仓库")
        
        # 成功返回
        task_result["success"] = True
        task_result["message"] = "数据获取成功"
        task_result["data"] = {
            "warehouses": warehouses
        }
        
        return task_result
        
    except Exception as e:
        logger.error(f"获取美团数据时出错: {e}")
        task_result["message"] = f"获取数据出错: {str(e)}"
        return task_result
    finally:
        # 关闭浏览器
        if driver:
            driver.quit()


def verify_meituan_auth(code: str, task_id: str) -> bool:
    """
    验证美团登录验证码
    
    Args:
        code: 验证码
        task_id: 任务ID
        
    Returns:
        bool: 验证是否成功
    """
    try:
        logger.info(f"验证美团验证码，任务ID: {task_id}")
        # TODO: 实现验证码验证功能
        return True
    except Exception as e:
        logger.error(f"验证美团验证码失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"msg": "验证美团验证码失败", "error_type": "verification_error"}
        )


def select_organization(browser, wait, target_org):
    """选择目标组织函数
    
    这是一个本地函数，用于处理select_organization未定义的问题
    """
    try:
        # 记录日志
        logger.info(f"尝试选择组织: {target_org}")
        
        # 实际选择组织的逻辑
        # 检查是否在选择机构页面
        if "selectorg" in browser.current_url:
            logger.info(f"在组织选择页面，将选择: {target_org}")
            
            # 使用JavaScript直接查找并点击目标机构
            js_code = f"""
            var found = false;
            var items = document.querySelectorAll('.org-item');
            for (var i = 0; i < items.length; i++) {{
                var nameDiv = items[i].querySelector('.name div:first-child');
                if (nameDiv && nameDiv.textContent.includes('{target_org}')) {{
                    var button = items[i].querySelector('button.saas-btn');
                    if (button) {{
                        button.click();
                        found = true;
                        break;
                    }}
                }}
            }}
            return found;
            """
            result = browser.execute_script(js_code)
            if result:
                logger.info("成功选择组织")
                time.sleep(2)
                return True
            else:
                logger.warning("未能找到目标组织")
                return False
        else:
            # 已经登录不需要选择机构
            logger.info("不在组织选择页面，跳过选择")
            return True
    except Exception as e:
        logger.error(f"选择组织失败: {e}")
        return False


def get_all_meituan_data(db: Session) -> Dict[str, Any]:
    """获取所有美团数据并处理
    
    Args:
        db: 数据库会话
        
    Returns:
        Dict[str, Any]: 结果信息
    """
    try:
        # 获取基础销售数据
        sales_data = fetch_meituan_data(db)
        
        # 验证是否需要手机验证码
        if not sales_data["success"] and sales_data.get("verification_needed", False):
            return {
                "success": False,
                "message": "需要手机验证码验证",
                "verification_task_id": sales_data.get("verification_task_id")
            }
        
        # 检查是否获取成功
        if not sales_data["success"]:
            return {
                "success": False,
                "message": f"获取美团数据失败: {sales_data['message']}"
            }
            
        # TODO: 处理获取到的数据
        
        return {
            "success": True,
            "message": "数据同步成功",
            "data_summary": {
                "warehouses": len(sales_data.get("data", {}).get("warehouses", []))
            }
        }
    except Exception as e:
        logger.error(f"同步美团数据出错: {e}")
        return {
            "success": False,
            "message": f"同步数据出错: {str(e)}"
        }


def extract_warehouses(response_data):
    """从API响应中提取仓库列表
    
    Args:
        response_data: API响应数据
        
    Returns:
        List[str]: 仓库名称列表
    """
    try:
        # 检查响应数据格式
        if not response_data or not isinstance(response_data, dict):
            return []
            
        # 尝试从数据中提取items
        items = response_data.get("data", {}).get("items", [])
        if not items:
            return []
            
        # 筛选含"仓"且不带括号的机构
        import re
        pattern = re.compile(r'^[^()（）]*仓[^()（）]*$')
        warehouses = [
            item.get("orgName", "")
            for item in items
            if pattern.search(item.get("orgName", ""))
        ]
        
        return warehouses
    except Exception as e:
        logger.error(f"提取仓库列表时出错: {e}")
        return []

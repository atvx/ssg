import json
import logging
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from selenium.webdriver.support.ui import WebDriverWait
import time
import os
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
import traceback
from urllib.parse import urlencode, quote
import re

from core.meituan.auth import login_with_phone, login_with_account, select_organization, check_login, choose_organization
from core.meituan.browser import init_chrome_driver
from core.meituan.navigation import navigate_to_business_overview, navigate_to_report_center, select_date
from core.meituan.data import get_all_meituan_data, perform_advanced_search
from utils.browser_utils import hide_all_popups, handle_iframe_slider, monitor_api_response

from config.settings import settings
from services.browser_service import get_browser
from celery import shared_task
from sqlalchemy.orm import Session
from utils.redis_utils import VerificationManager
from db.database import get_db, SessionLocal
from models.user import User

# 配置日志
logger = logging.getLogger(__name__)

# 定义常量
LOGIN_URL = settings.MEITUAN_CONFIG["LOGIN_URL"]
REPORT_CENTER_URL = settings.MEITUAN_CONFIG["BUSINESS_OVERVIEW_URL"]


@shared_task(bind=True, max_retries=3)
def fetch_meituan_data_task(self):
    """Celery任务：获取美团销售数据"""
    logger.info("开始执行美团数据抓取任务")
    try:
        # 获取数据库会话
        db = SessionLocal()
        
        # 获取系统管理员用户
        admin_user = db.query(User).filter(User.is_superuser == True).first()
        admin_id = admin_user.id if admin_user else None
        
        # 获取美团销售数据
        task_data = fetch_meituan_data(db, user_id=admin_id)
        return task_data
    except Exception as e:
        logger.error(f"获取美团数据失败: {e}")
        logger.error(traceback.format_exc())
        # 重试，退避策略: 5分钟, 10分钟, 15分钟
        retry_countdown = (self.request.retries + 1) * 300
        self.retry(exc=e, countdown=retry_countdown)


def fetch_meituan_data(db: Session, date: Optional[str] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
    """获取美团销售数据
    
    Args:
        db: 数据库会话
        date: 查询日期（格式为YYYY-MM-DD），为空时默认为当天
        user_id: 用户ID，用于获取第三方平台账号信息（可选）
        
    Returns:
        Dict[str, Any]: 提取的数据，格式为：
        {
            "success": true,
            "message": "获取数据成功",
            "date": "2025-05-19",
            "platform": "meituan",
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
    driver = None
    task_result = {
        "success": False,
        "message": "",
        "platform": "meituan",
        "data": []
    }
    
    # 增加详细日志，追踪日期参数
    logger.info(f"======= fetch_meituan_data 被调用，接收到日期参数：'{date}'，用户ID：{user_id} =======")
    
    # 处理日期参数
    today = datetime.now().date().isoformat()
    
    # 验证传入的日期格式，确保是YYYY-MM-DD
    if date:
        try:
            # 验证日期格式
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            query_date = date_obj.strftime("%Y-%m-%d")  # 标准化日期格式
            logger.info(f"使用传入的日期参数: {date} -> {query_date}")
        except ValueError:
            logger.warning(f"传入的日期格式错误: {date}，将使用当前日期")
            query_date = today
    else:
        query_date = today
        logger.info(f"未传入日期参数，使用当前日期: {query_date}")
    
    # 确保日期字符串格式为YYYY-MM-DD
    if query_date != date and date is not None:
        logger.warning(f"⚠️ 注意：传入的日期参数 '{date}' 已被转换为 '{query_date}'")
    
    # 将日期信息添加到结果中
    task_result["date"] = query_date
    
    logger.info(f"获取美团数据，查询日期: {query_date}")
    
    try:
        # 初始化浏览器，开启API监控
        # 创建一个包含所有参数的配置字典
        browser_config = {
            "USER_DATA_DIR": settings.CHROME_USER_DATA_DIR,
            "HEADLESS": False,
            "MONITOR_API_RESPONSE": True,
            "MONITOR_SCOPES": [".*pos\\.meituan\\.com.*"]  # 匹配所有美团POS域名下的请求
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
                "cookies_meituan.json",
                db=db,
                user_id=user_id,
                platform="meituan"
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
            # 1. 先导航到报表中心
            navigate_success = navigate_to_report_center(driver, wait)
            if not navigate_success:
                logger.warning("导航到报表中心失败，尝试直接导航到业务概览页面")
                
            # 2. 然后导航到业务概览页面
            logger.info(f"导航到业务概览页面: {settings.MEITUAN_CONFIG['BUSINESS_OVERVIEW_URL']}")
            driver.get(settings.MEITUAN_CONFIG["BUSINESS_OVERVIEW_URL"])
            time.sleep(2)
            
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
        
        # 从API获取仓库列表
        logger.info("获取仓库列表...")
        
        # 使用selenium-wire监控API响应
        warehouse_response = monitor_api_response(
            driver,
            "/tree/paged/query",  # URL匹配模式
            timeout=120,  # 超时时间
            methods=['POST']
        )

        # 处理仓库数据
        warehouses = extract_warehouses(warehouse_response)
        if not warehouses:
            logger.error("未找到任何仓库")
            task_result["message"] = "API响应中未找到仓库数据"
            return task_result
            
        logger.info(f"成功获取 {len(warehouses)} 个仓库")
        
        # 查询每个仓库的销售数据
        logger.info("开始查询各仓库销售数据...")
        sales_results = []
        
        # 对每个仓库执行高级查询
        try:
            from tqdm import tqdm
            api_config = {
                "API_TIMEOUT": 60,
                "BUSINESS_SUMMARY_URL": "https://pos.meituan.com/web/api/v2/reports/combine/business-summary-page",
            }
            
            def patched_monitor_api_response(driver, url, max_wait_time=None, methods=None, start_time=None, **kwargs):
                timeout = max_wait_time if max_wait_time is not None else 60
                return monitor_api_response(driver, url, timeout=timeout, methods=methods, start_time=start_time, **kwargs)
            
            import core.meituan.data
            original_monitor_api_response = core.meituan.data.monitor_api_response
            core.meituan.data.monitor_api_response = patched_monitor_api_response
            
            time.sleep(3)
            
            # 在遍历仓库前，设置一次查询日期
            logger.info(f"设置查询日期: {query_date}")
            try:
                # 确保日期格式正确 (YYYY-MM-DD)
                try:
                    date_obj = datetime.strptime(query_date, "%Y-%m-%d")
                    formatted_date = date_obj.strftime("%Y-%m-%d")  # 标准化日期格式
                    logger.info(f"格式化后的日期: {formatted_date}")
                except ValueError:
                    logger.error(f"日期格式错误: {query_date}，应为YYYY-MM-DD格式")
                    task_result["message"] = "日期格式错误，应为YYYY-MM-DD格式"
                    return task_result
                
                logger.info(f"调用select_date设置日期: {formatted_date}")
                select_date(driver, formatted_date)
                time.sleep(2)
            except Exception as e:
                logger.error(f"设置日期时出错: {e}")
                logger.error(traceback.format_exc())
                logger.warning("将使用默认日期进行查询")
            
            # 确保只设置一次日期后，开始遍历仓库执行查询
            logger.info(f"开始遍历查询 {len(warehouses)} 个仓库的销售数据，每个仓库只会执行一次查询操作")
            for name in tqdm(warehouses, desc="处理进度", unit="仓", ncols=100, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"):
                logger.info(f"正在查询仓库【{name}】的销售数据")
                
                # 执行高级查询，确保每个仓库只查询一次
                result = perform_advanced_search(driver, wait, target_org=name, config=api_config)
                sales_results.append(result)
                logger.info(f"仓库【{name}】销售数据: 收入={result['incomeAmt']}元, 销售车辆={result['salesCartCount']}, 平均收入={result['avgIncomeAmt']}元")
                
                # 添加短暂延迟，确保下一次查询不会受到影响
                time.sleep(1)
            
            # 恢复原始函数
            core.meituan.data.monitor_api_response = original_monitor_api_response
            
        except Exception as e:
            logger.error(f"查询销售数据时出错: {e}")
            logger.error(traceback.format_exc())
            if not sales_results:
                task_result["message"] = f"查询销售数据时出错: {str(e)}"
                return task_result
        
        # 成功返回
        task_result["success"] = True
        task_result["message"] = "数据获取成功"
        task_result["data"] = sales_results
        
        print(task_result)
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


def get_all_meituan_data(db: Session, date: Optional[str] = None) -> Dict[str, Any]:
    """获取所有美团数据并处理
    
    Args:
        db: 数据库会话
        date: 查询日期（格式为YYYY-MM-DD），为空时默认为当天
    
    Returns:
        Dict[str, Any]: 结果信息
    """
    try:
        # 获取系统管理员用户ID
        admin_user = db.query(User).filter(User.is_superuser == True).first()
        admin_id = admin_user.id if admin_user else None
        
        # 获取基础销售数据
        sales_data = fetch_meituan_data(db, date=date, user_id=admin_id)
        
        # 验证是否需要手机验证码
        if not sales_data["success"]:
            return {
                "success": False,
                "message": f"获取美团数据失败: {sales_data['message']}",
                "platform": "meituan"
            }
            
        # 获取销售结果数据
        sales_results = sales_data.get("data", [])
        
        # 计算总销售额和总销售数量
        total_income = sum(item.get("incomeAmt", 0) for item in sales_results)
        total_sales_count = sum(item.get("salesCartCount", 0) for item in sales_results)
        
        # 计算平均销售额（如果有销售）
        avg_income = 0
        if total_sales_count > 0:
            avg_income = total_income / total_sales_count
            
        # 构建结果摘要
        summary = {
            "warehouses_count": len(sales_results),
            "total_income": round(total_income, 2),
            "total_sales_count": total_sales_count,
            "avg_income": round(avg_income, 2)
        }
        
        # logger.info(f"美团数据同步完成: {summary}")
        
        # 返回与fetch_meituan_data相同格式的数据，增加摘要信息
        return {
            "success": sales_data["success"],
            "message": sales_data["message"],
            "platform": "meituan",
            "date": sales_data.get("date", ""),
            "data": sales_results,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"同步美团数据出错: {e}")
        return {
            "success": False,
            "message": f"同步数据出错: {str(e)}",
            "platform": "meituan"
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

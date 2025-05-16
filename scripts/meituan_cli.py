#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
import os
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import MEITUAN_CONFIG, LOGIN_MODE
from core.meituan.browser import init_chrome_driver
from core.meituan.auth import login_with_phone, login_with_account, select_organization
from core.meituan.navigation import navigate_to_report_center, navigate_to_business_overview
from core.meituan.data import get_all_meituan_data
from utils.file_utils import load_cookies


def main(date=None):
    """主函数：执行完整的登录和数据获取流程"""
    print("启动美团POS自动化工具...")
    
    driver = None
    force_new_session = False
    retry_count = 0
    max_retries = 2
    
    while retry_count <= max_retries:
        try:
            # 初始化浏览器
            try:
                driver = init_chrome_driver(MEITUAN_CONFIG, force_new_session)
                wait = WebDriverWait(driver, MEITUAN_CONFIG["WAIT_TIME"])
            except Exception as e:
                if "user data directory is already in use" in str(e).lower():
                    print("无法自动关闭Chrome实例，尝试使用强制新会话模式...")
                    force_new_session = True
                    retry_count += 1
                    continue
                elif retry_count == 0:
                    print("浏览器初始化失败，尝试使用强制新会话模式...")
                    force_new_session = True
                    retry_count += 1
                    continue
                else:
                    print("浏览器启动失败。请确保没有Chrome实例正在运行，然后重试。")
                    return None
            
            # 打开登录页面
            driver.get(MEITUAN_CONFIG["LOGIN_URL"])
            print("正在加载登录页面...")
            
            # 判断是否已经登录
            already_logged_in = False
            cookies_loaded = False
            
            # 只有在非强制新会话模式下才尝试加载cookie
            if not force_new_session:
                # 尝试加载cookies
                try:
                    cookies_loaded = load_cookies(driver, MEITUAN_CONFIG["COOKIES_FILE"], verify=True)
                    if cookies_loaded:
                        print("已加载之前的登录信息，尝试刷新页面...")
                        # 重新加载页面，检查是否已登录
                        driver.refresh()
                        time.sleep(3)
                except Exception as e:
                    print(f"加载cookies时出错: {e}")
                    cookies_loaded = False
                
                # 检查是否成功保持登录状态
                try:
                    if '/login' not in driver.current_url and '/auth' not in driver.current_url:
                        # 尝试更可靠的方式检测登录状态
                        logged_in = driver.execute_script("""
                        return document.cookie.indexOf('token') > -1 || 
                               document.cookie.indexOf('auth') > -1 ||
                               window.localStorage.getItem('token') !== null ||
                               !window.location.href.includes('login');
                        """)
                        
                        if logged_in:
                            print("成功检测到登录状态")
                            already_logged_in = True
                except Exception as e:
                    print(f"检查登录状态时出错: {e}")
            
            # 如果没有成功登录，需要重新登录
            login_success = already_logged_in
            
            if not already_logged_in:
                # 根据登录方式选择
                if LOGIN_MODE == 0:
                    print("使用手机号登录...")
                    login_success = login_with_phone(driver, wait, MEITUAN_CONFIG["PHONE_NUMBER"])
                else:
                    print("使用账号密码登录...")
                    login_success = login_with_account(driver, wait, MEITUAN_CONFIG["COOKIES_FILE"])
                    
                # 如果登录失败且不是强制新会话，尝试使用新会话
                if not login_success and not force_new_session:
                    print("登录失败，尝试使用新会话模式...")
                    force_new_session = True
                    if driver:
                        driver.quit()
                        driver = None
                    retry_count += 1
                    continue
            
            if login_success:
                # 选择机构
                org_selected = False
                try:
                    org_selected = select_organization(driver, wait, MEITUAN_CONFIG["TARGET_ORG"])
                    if org_selected:
                        print("机构选择成功")
                    else:
                        print("未能选择机构，但将继续执行")
                except Exception as e:
                    print(f"选择机构时出错: {e}")
                
                # 导航到报表中心
                report_center_success = False
                try:
                    report_center_success = navigate_to_report_center(driver, wait)
                    if report_center_success:
                        print("成功导航到报表中心")
                    else:
                        print("无法导航到报表中心，但将继续尝试")
                except Exception as e:
                    print(f"导航到报表中心时出错: {e}")
                
                # 导航到营业概览并获取数据
                try:
                    if navigate_to_business_overview(driver, wait, MEITUAN_CONFIG):
                        # 获取所有仓库数据
                        results = get_all_meituan_data(driver, wait, MEITUAN_CONFIG, date)
                        print(f"成功获取 {len(results)} 个仓库的销售数据")
                        print(f"数据已保存到: {MEITUAN_CONFIG['OUTPUT_FILE']}")
                except Exception as e:
                    print(f"处理营业概览数据时出错: {e}")
                    import traceback
                    traceback.print_exc()
                    return None
                
                # 成功完成所需任务，跳出重试循环
                break
            else:
                print("登录失败")
                
                # 如果是最后一次重试，打印更详细的错误信息
                if retry_count == max_retries:
                    print("=" * 40)
                    print("诊断信息:")
                    cookies_file = MEITUAN_CONFIG["COOKIES_FILE"]
                    user_data_dir = MEITUAN_CONFIG["USER_DATA_DIR"]
                    print(f"- Cookie文件状态: {'存在' if os.path.exists(cookies_file) else '不存在'} ({cookies_file})")
                    print(f"- 用户数据目录状态: {'存在' if os.path.exists(user_data_dir) else '不存在'} ({user_data_dir})")
                    print("- 当前URL:", driver.current_url if driver else "无")
                    print("=" * 40)
                
                # 如果不是最后一次重试，尝试强制新会话模式
                if retry_count < max_retries:
                    print(f"尝试重新登录 (尝试 {retry_count+1}/{max_retries+1})")
                    force_new_session = True
                    if driver:
                        driver.quit()
                        driver = None
                    retry_count += 1
                    continue
                return None
                
        except Exception as e:
            print(f"运行过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            
            # 如果不是最后一次重试，尝试使用新会话
            if retry_count < max_retries:
                print(f"尝试使用新会话重新运行 (尝试 {retry_count+1}/{max_retries+1})")
                force_new_session = True
                if driver:
                    driver.quit()
                    driver = None
                retry_count += 1
                continue
            else:
                return None
        finally:
            # 每次重试之前，确保关闭之前的浏览器实例
            if driver and retry_count < max_retries and not login_success:
                driver.quit()
                driver = None
    
    # 关闭浏览器
    if driver:
        driver.quit()
    
    print("美团POS数据获取完成")
    return True


if __name__ == "__main__":
    # 获取命令行参数中的日期（如果有）
    date_arg = None
    if len(sys.argv) > 1:
        date_arg = sys.argv[1]
        try:
            # 验证日期格式
            datetime.strptime(date_arg, '%Y-%m-%d')
        except ValueError:
            print(f"错误: 日期格式无效，请使用YYYY-MM-DD格式")
            sys.exit(1)
    
    # 运行主程序
    success = main(date_arg)
    if not success:
        sys.exit(1) 
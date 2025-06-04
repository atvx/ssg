#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Selenium环境配置与验证脚本
此脚本用于确保Chrome和ChromeDriver正确安装和配置
"""

import os
import time
import logging
import subprocess
from pathlib import Path
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

logger = logging.getLogger(__name__)

def download_latest_chromedriver():
    """下载并配置最新版本的ChromeDriver"""
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service

        # 禁用webdriver_manager的日志
        os.environ['WDM_LOG_LEVEL'] = '0'
        os.environ['WDM_PRINT_FIRST_LINE'] = 'False'
        os.environ['WDM_SSL_VERIFY'] = '0'
        
        # 下载ChromeDriver
        print("正在配置Selenium驱动程序...")
        driver_path = ChromeDriverManager().install()
        
        # 创建符号链接
        subprocess.run(['ln', '-sf', driver_path, '/usr/local/bin/chromedriver'])
        subprocess.run(['chmod', '+x', '/usr/local/bin/chromedriver'])
        print(f"ChromeDriver已安装在: {driver_path}")
        print("已创建chromedriver符号链接到/usr/local/bin/chromedriver")
        
        # 验证chrome和chromedriver是否工作
        print("验证Chrome设置...")
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print(f"ChromeDriver服务启动成功 (端口: {service.port})")
        driver.quit()
        print("ChromeDriver服务已验证")
        
        return driver_path
    except Exception as e:
        print(f"配置ChromeDriver时发生错误: {str(e)}")
        traceback.print_exc()
        return None

def ensure_temp_dirs():
    """确保必要的临时目录存在"""
    try:
        # 确保Chrome用户数据目录存在
        chrome_user_data = Path("/app/chrome_user_data")
        chrome_user_data.mkdir(exist_ok=True)
        subprocess.run(['chmod', '-R', '777', str(chrome_user_data)])
        
        # 确保Chrome临时目录存在
        chrome_tmp = Path("/tmp/chrome_tmp")
        chrome_tmp.mkdir(exist_ok=True)
        subprocess.run(['chmod', '-R', '777', str(chrome_tmp)])
        
    except Exception as e:
        print(f"创建目录时发生错误: {str(e)}")

def main():
    """主函数"""
    # 确保目录存在
    ensure_temp_dirs()
    
    # 下载并配置ChromeDriver
    driver_path = download_latest_chromedriver()
    
    if driver_path:
        print(f"Selenium驱动程序设置完成，路径为: {driver_path}")
    else:
        print("Selenium驱动程序设置失败!")
        exit(1)

if __name__ == "__main__":
    main() 
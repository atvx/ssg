#!/usr/bin/env python
"""
Selenium设置辅助脚本
这个脚本会在运行时自动下载和配置chromedriver，并设置必要的环境变量
"""

import os
import sys
import subprocess
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

def setup_selenium_drivers():
    """设置Selenium驱动程序并返回正确的配置"""
    print("正在配置Selenium驱动程序...")
    
    # 设置环境变量
    os.environ['WDM_LOG_LEVEL'] = '0'  # 减少webdriver-manager的日志输出
    os.environ['WDM_SSL_VERIFY'] = '0'  # 避免SSL验证问题
    
    try:
        # 尝试使用webdriver-manager下载并设置chromedriver
        driver_path = ChromeDriverManager().install()
        print(f"ChromeDriver已安装在: {driver_path}")
        
        # 设置环境变量，使其他程序能够找到驱动程序
        os.environ['CHROMEDRIVER_PATH'] = driver_path
        os.environ['PATH'] = f"{os.path.dirname(driver_path)}:{os.environ.get('PATH', '')}"
        
        # 创建符号链接到标准位置
        try:
            subprocess.run(['ln', '-sf', driver_path, '/usr/local/bin/chromedriver'])
            subprocess.run(['chmod', '+x', '/usr/local/bin/chromedriver'])
            print("已创建chromedriver符号链接到/usr/local/bin/chromedriver")
        except Exception as e:
            print(f"创建符号链接时出错: {e}")
        
        # 测试浏览器启动
        print("测试Chrome浏览器启动...")
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        # 添加更多参数提高稳定性
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-dev-tools')
        options.add_argument('--single-process')
        options.add_argument('--disable-background-networking')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--disable-infobars')
        options.add_argument('--remote-debugging-port=9222')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        print(f"Chrome版本: {driver.capabilities['browserVersion']}")
        driver.quit()
        print("Chrome测试成功!")
        
        return {
            'driver_path': driver_path,
            'success': True
        }
    except Exception as e:
        print(f"设置Chrome驱动程序时出错: {e}")
        
        # 尝试使用系统安装的chromedriver
        try:
            subprocess.run(['which', 'chromedriver'], check=True, capture_output=True)
            system_driver = subprocess.getoutput('which chromedriver')
            print(f"使用系统安装的chromedriver: {system_driver}")
            os.environ['CHROMEDRIVER_PATH'] = system_driver
            return {
                'driver_path': system_driver,
                'success': True
            }
        except Exception as e2:
            print(f"查找系统chromedriver时出错: {e2}")
            return {
                'success': False,
                'error': str(e)
            }

if __name__ == "__main__":
    result = setup_selenium_drivers()
    if result['success']:
        print(f"Selenium驱动程序设置完成，路径为: {result['driver_path']}")
        sys.exit(0)
    else:
        print(f"Selenium驱动程序设置失败: {result.get('error', '未知错误')}")
        sys.exit(1) 
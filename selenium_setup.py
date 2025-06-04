#!/usr/bin/env python
"""
Selenium设置辅助脚本
这个脚本会在运行时自动下载和配置chromedriver，并设置必要的环境变量
"""

import os
import sys
import subprocess
import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

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
            subprocess.run(['ln', '-sf', driver_path, '/usr/local/bin/chromedriver'], check=False)
            subprocess.run(['chmod', '+x', '/usr/local/bin/chromedriver'], check=False)
            print("已创建chromedriver符号链接到/usr/local/bin/chromedriver")
        except Exception as e:
            print(f"创建符号链接时出错: {e}")
        
        # 测试Chrome设置但不实际启动浏览器
        print("验证Chrome设置...")
        
        # 确保临时目录存在
        tmp_dir = "/tmp/chrome_tmp"
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir, exist_ok=True)
            os.chmod(tmp_dir, 0o777)
        
        # 配置简化的选项，最小化启动时间
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument(f'--user-data-dir={tmp_dir}')
        options.add_argument('--disable-dev-tools')
        options.add_argument('--window-size=800,600')  # 使用更小的窗口
        options.add_argument('--disable-features=VizDisplayCompositor')
        # 减少响应超时
        options.add_argument('--remote-debugging-port=9222')
        options.page_load_strategy = 'none'  # 不等待页面加载完成
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # 使用try-except验证chromedriver能否创建服务
        try:
            service = Service(executable_path=driver_path)
            service.start()
            print(f"ChromeDriver服务启动成功 (端口: {service.port})")
            service.stop()
            print("ChromeDriver服务已验证")
            
            return {
                'driver_path': driver_path,
                'success': True
            }
        except Exception as e:
            print(f"ChromeDriver服务验证出错: {e}")
            # 尝试手动验证chromedriver是否可执行
            try:
                result = subprocess.run([driver_path, '--version'], 
                                       capture_output=True, 
                                       text=True, 
                                       timeout=10,
                                       check=False)
                if result.returncode == 0:
                    print(f"ChromeDriver验证成功: {result.stdout.strip()}")
                    return {
                        'driver_path': driver_path,
                        'success': True
                    }
                else:
                    print(f"ChromeDriver版本检查失败: {result.stderr}")
            except Exception as e2:
                print(f"ChromeDriver执行检查出错: {e2}")
        
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
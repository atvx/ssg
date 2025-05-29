from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver as wire_webdriver
import os
import time
import socket
import random
import threading
import signal
import platform

from config.settings import settings
from utils.file_utils import kill_chrome_processes


class TimeoutException(Exception):
    """自定义超时异常"""
    pass


def timeout_handler(signum, frame):
    """超时信号处理函数"""
    print("Chrome启动超时！")
    raise TimeoutException("Chrome启动超时")


def init_chrome_driver(config, force_new_session=False):
    """初始化Chrome浏览器
    
    Args:
        config: 配置字典
        force_new_session (bool): 如果为True，不使用现有的用户数据目录
    """
    chrome_options = Options()
    
    # 必要的安全设置
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Docker环境优化
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--single-process")  # 减少复杂性
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-dev-tools")
    chrome_options.add_argument("--headless")  # 确保使用无头模式
    
    # 内存和性能优化
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--safebrowsing-disable-auto-update")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    # 窗口大小设置
    chrome_options.add_argument("--window-size=1920,1080")
    
    # User-Agent设置
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # 防止自动化检测
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # 使用临时目录
    chrome_options.add_argument("--disk-cache-dir=/tmp/chrome_tmp")
    
    # 使用用户数据目录保持登录状态
    use_user_data_dir = not force_new_session
    if use_user_data_dir:
        try:
            # 检查默认用户数据目录是否存在
            base_user_data_dir = os.path.abspath(config.get("USER_DATA_DIR", settings.CHROME_USER_DATA_DIR))
            
            # 为每个容器/进程创建唯一的用户数据目录
            hostname = socket.gethostname()
            random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
            user_data_dir = f"{base_user_data_dir}_{hostname}_{random_suffix}"
            
            # 先尝试删除目录（如果存在），然后创建新目录
            if os.path.exists(user_data_dir):
                import shutil
                shutil.rmtree(user_data_dir, ignore_errors=True)
                
            try:
                os.makedirs(user_data_dir, exist_ok=True)
                os.chmod(user_data_dir, 0o777)  # 设置777权限
                print(f"创建用户数据目录: {user_data_dir}")
            except Exception as mkdir_err:
                print(f"创建目录时出错: {mkdir_err}")
                
            # 使用唯一目录
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        except Exception as e:
            print(f"设置用户数据目录时出错: {e}，将使用临时用户配置文件")
            use_user_data_dir = False
    else:
        print("使用新会话模式，不加载用户数据目录")
    
    # 抑制控制台错误消息
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--silent")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
    
    driver = None
    
    # 设置超时信号（仅在类Unix系统有效）
    if platform.system() != "Windows":
        # 保存旧的信号处理器
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        # 设置30秒超时
        signal.alarm(30)
    
    # 首次尝试启动浏览器
    try:
        print(f"开始启动Chrome浏览器，当前时间: {time.strftime('%H:%M:%S')}")
        
        # 使用Service类指定chromedriver路径
        chrome_driver_path = "/usr/local/bin/chromedriver"
        if os.path.exists(chrome_driver_path):
            print(f"使用指定的ChromeDriver路径: {chrome_driver_path}")
            service = Service(executable_path=chrome_driver_path)
        else:
            print("未找到指定ChromeDriver，使用自动检测")
            service = Service()
        
        monitor_api = config.get("MONITOR_API_RESPONSE", False)
        if monitor_api:
            # 优化selenium-wire配置
            seleniumwire_options = {
                'disable_encoding': True,  # 禁用内容编码，以便能够读取响应体
                'suppress_connection_errors': True,  # 抑制连接错误
                'verify_ssl': False,  # 不验证SSL证书，避免某些HTTPS请求问题
                'request_storage': 'memory',  # 使用内存存储请求，提高性能
                'request_storage_max_size': 100,  # 最多存储100个请求，避免内存问题
                'connection_timeout': 30  # 连接超时时间设置为30秒
            }
            
            # 设置请求过滤范围
            scopes = config.get("MONITOR_SCOPES", ['.*pos\\.meituan\\.com.*'])
            
            # 创建driver
            print("使用selenium-wire启动Chrome...")
            driver = wire_webdriver.Chrome(options=chrome_options, 
                                          service=service,
                                          seleniumwire_options=seleniumwire_options)
            
            # 设置请求过滤
            driver.scopes = scopes
            print(f"已启用API监控，监控范围: {scopes}")
        else:
            print("使用标准selenium启动Chrome...")
            driver = webdriver.Chrome(options=chrome_options, service=service)
            
        # 防止检测
        print("设置防检测选项...")
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        
        print(f"Chrome启动成功，当前时间: {time.strftime('%H:%M:%S')}")
        
        # 重置超时信号
        if platform.system() != "Windows":
            signal.alarm(0)
            # 恢复旧的信号处理器
            signal.signal(signal.SIGALRM, old_handler)
            
        return driver
    except Exception as e:
        # 重置超时信号
        if platform.system() != "Windows":
            signal.alarm(0)
            # 恢复旧的信号处理器
            signal.signal(signal.SIGALRM, old_handler)
            
        error_message = str(e).lower()
        print(f"Chrome启动出错: {error_message}")
        
        # 检查是否是超时异常
        if isinstance(e, TimeoutException) or "timeout" in error_message:
            print("Chrome启动超时，尝试清理环境后重启...")
            kill_chrome_processes()
            time.sleep(3)
            
            # 重新尝试启动Chrome，使用更简化的配置
            try:
                print("使用简化配置重新启动Chrome...")
                chrome_options = Options()
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--disable-extensions")
                chrome_options.add_argument("--disable-infobars")
                
                chrome_driver_path = "/usr/local/bin/chromedriver"
                if os.path.exists(chrome_driver_path):
                    service = Service(executable_path=chrome_driver_path)
                else:
                    service = Service()
                
                monitor_api = config.get("MONITOR_API_RESPONSE", False)
                if monitor_api:
                    # 使用极简配置
                    seleniumwire_options = {
                        'disable_encoding': True,
                        'suppress_connection_errors': True,
                        'verify_ssl': False,
                        'request_storage': 'memory',
                        'request_storage_max_size': 10,
                        'connection_timeout': 15
                    }
                    
                    # 设置请求过滤范围
                    scopes = config.get("MONITOR_SCOPES", ['.*pos\\.meituan\\.com.*'])
                    
                    # 创建driver
                    driver = wire_webdriver.Chrome(options=chrome_options, 
                                                 service=service,
                                                 seleniumwire_options=seleniumwire_options)
                    driver.scopes = scopes
                else:
                    driver = webdriver.Chrome(options=chrome_options, service=service)
                
                return driver
            except Exception as inner_e:
                print(f"使用简化配置启动Chrome也失败: {inner_e}")
                raise Exception(f"Chrome启动失败，请检查系统环境: {inner_e}")
        
        # 检查是否是用户数据目录被占用的错误
        elif "user data directory is already in use" in error_message and use_user_data_dir:
            print("检测到Chrome实例已在运行，正在尝试关闭...")
            
            # 尝试终止现有Chrome进程
            kill_chrome_processes()
            
            # 等待进程完全终止
            time.sleep(2)
            
            # 重新尝试启动Chrome，但不使用用户数据目录
            try:
                # 移除用户数据目录选项
                chrome_options = Options()
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--disable-software-rasterizer")
                chrome_options.add_argument("--disable-setuid-sandbox")
                chrome_options.add_argument("--single-process")
                chrome_options.add_argument("--disable-extensions")
                chrome_options.add_argument("--disable-infobars")
                chrome_options.add_argument("--disable-dev-tools")
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--disable-features=TranslateUI")
                chrome_options.add_argument("--disable-notifications")
                chrome_options.add_argument("--disable-background-networking")
                chrome_options.add_argument("--safebrowsing-disable-auto-update")
                chrome_options.add_argument("--disable-sync")
                chrome_options.add_argument("--disable-default-apps")
                chrome_options.add_argument("--ignore-certificate-errors")
                chrome_options.add_argument("--remote-debugging-port=9222")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument(
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option("useAutomationExtension", False)
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_argument("--log-level=3")
                chrome_options.add_argument("--silent")
                chrome_options.add_argument("--disable-logging")
                chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
                
                print("使用新会话模式启动Chrome...")
                
                # 使用Service类指定chromedriver路径
                chrome_driver_path = "/usr/local/bin/chromedriver"
                if os.path.exists(chrome_driver_path):
                    service = Service(executable_path=chrome_driver_path)
                else:
                    service = Service()
                
                monitor_api = config.get("MONITOR_API_RESPONSE", False)
                if monitor_api:
                    # 优化selenium-wire配置
                    seleniumwire_options = {
                        'disable_encoding': True,
                        'suppress_connection_errors': True,
                        'verify_ssl': False,
                        'request_storage': 'memory',
                        'request_storage_max_size': 100,
                        'connection_timeout': 30
                    }
                    
                    # 设置请求过滤范围
                    scopes = config.get("MONITOR_SCOPES", ['.*pos\\.meituan\\.com.*'])
                    
                    # 创建driver
                    driver = wire_webdriver.Chrome(options=chrome_options, 
                                                 service=service,
                                                 seleniumwire_options=seleniumwire_options)
                    
                    # 设置请求过滤
                    driver.scopes = scopes
                else:
                    driver = webdriver.Chrome(options=chrome_options, service=service)
                
                # 防止检测
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
                
                return driver
            except Exception as inner_e:
                raise Exception(f"无法启动Chrome: {inner_e}")
        else:
            # 其他类型的错误，抛出异常
            raise Exception(f"启动Chrome时出错: {e}") 
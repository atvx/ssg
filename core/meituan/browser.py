from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from seleniumwire import webdriver as wire_webdriver
import os
import time

from config.settings import settings
from utils.file_utils import kill_chrome_processes


def init_chrome_driver(config, force_new_session=False):
    """初始化Chrome浏览器
    
    Args:
        config: 配置字典
        force_new_session (bool): 如果为True，不使用现有的用户数据目录
    """
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 添加以下代码，处理无头模式
    if config.get("HEADLESS", False):
        chrome_options.add_argument("--headless=new")  # 使用新的headless模式
        print("启用无头模式运行Chrome")
    
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # 使用用户数据目录保持登录状态
    use_user_data_dir = not force_new_session
    if use_user_data_dir:
        try:
            # 检查默认用户数据目录是否存在
            user_data_dir = os.path.abspath(config.get("USER_DATA_DIR", settings.CHROME_USER_DATA_DIR))
            if not os.path.exists(user_data_dir):
                os.makedirs(user_data_dir, exist_ok=True)
                print(f"创建用户数据目录: {user_data_dir}")
            
            # 使用固定目录
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        except Exception as e:
            print(f"设置用户数据目录时出错，将使用临时用户配置文件")
            use_user_data_dir = False
    else:
        print("使用新会话模式，不加载用户数据目录")
    
    # 抑制控制台错误消息
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--silent")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
    
    # 首次尝试启动浏览器
    try:
        monitor_api = config.get("MONITOR_API_RESPONSE", False)
        if monitor_api:
            # 优化selenium-wire配置
            seleniumwire_options = {
                'disable_encoding': True,  # 禁用内容编码，以便能够读取响应体
                'suppress_connection_errors': True,  # 抑制连接错误
                'verify_ssl': False,  # 不验证SSL证书，避免某些HTTPS请求问题
                'request_storage': 'memory',  # 使用内存存储请求，提高性能
                'request_storage_max_size': 100  # 最多存储100个请求，避免内存问题
            }
            
            # 设置请求过滤范围
            scopes = config.get("MONITOR_SCOPES", [r'.*pos\.meituan\.com.*'])
            
            # 创建driver
            driver = wire_webdriver.Chrome(options=chrome_options, seleniumwire_options=seleniumwire_options)
            
            # 设置请求过滤
            driver.scopes = scopes
            print(f"已启用API监控，监控范围: {scopes}")
            browser_version = driver.capabilities['browserVersion']
            driver_version = driver.capabilities['chrome']['chromedriverVersion'].split(' ')[0]
            print(f"Chrome浏览器版本: {browser_version}")
            print(f"ChromeDriver版本: {driver_version}")
        else:
            driver = webdriver.Chrome(options=chrome_options)
            
        # 防止检测
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        
        return driver
    except Exception as e:
        error_message = str(e).lower()
        
        # 检查是否是用户数据目录被占用的错误
        if "user data directory is already in use" in error_message and use_user_data_dir:
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
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option("useAutomationExtension", False)
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_argument("--log-level=3")
                chrome_options.add_argument("--silent")
                chrome_options.add_argument("--disable-logging")
                chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
                
                print("使用新会话模式启动Chrome...")
                
                monitor_api = config.get("MONITOR_API_RESPONSE", False)
                if monitor_api:
                    # 优化selenium-wire配置
                    seleniumwire_options = {
                        'disable_encoding': True,
                        'suppress_connection_errors': True,
                        'verify_ssl': False,
                        'request_storage': 'memory',
                        'request_storage_max_size': 100
                    }
                    
                    # 设置请求过滤范围
                    scopes = config.get("MONITOR_SCOPES", [r'.*pos\.meituan\.com.*'])
                    
                    # 创建driver
                    driver = wire_webdriver.Chrome(options=chrome_options, seleniumwire_options=seleniumwire_options)
                    
                    # 设置请求过滤
                    driver.scopes = scopes
                else:
                    driver = webdriver.Chrome(options=chrome_options)
                
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
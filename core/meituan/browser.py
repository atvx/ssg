from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver as wire_webdriver
import os
import time
import subprocess
from retry import retry
from tenacity import retry as tenacity_retry
from tenacity import stop_after_attempt, wait_fixed, retry_if_exception_type

from config.settings import settings
from utils.file_utils import kill_chrome_processes


# 重试装饰器，针对浏览器启动
@tenacity_retry(
    stop=stop_after_attempt(3),  # 最多尝试3次
    wait=wait_fixed(2),  # 每次等待2秒
    retry=retry_if_exception_type((Exception)),  # 任何异常都重试
    reraise=True  # 最后一次失败时抛出原始异常
)
def init_chrome_driver(config, force_new_session=False):
    """初始化Chrome浏览器
    
    Args:
        config: 配置字典
        force_new_session (bool): 如果为True，不使用现有的用户数据目录
    """
    # 在启动前清理可能的僵尸Chrome进程
    try:
        kill_chrome_processes()
        time.sleep(1)  # 等待进程完全终止
    except Exception as e:
        print(f"清理Chrome进程时出错（非致命）: {e}")

    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1280,800")  # 减小窗口大小
    
    # 添加以下代码，处理无头模式
    if config.get("HEADLESS", False):
        chrome_options.add_argument("--headless=new")  # 使用新的headless模式
        # 添加解决DevToolsActivePort问题的参数
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        # 禁用GPU相关功能
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        # 临时目录权限问题
        data_dir = "/tmp/chrome_tmp"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            os.chmod(data_dir, 0o777)
        chrome_options.add_argument(f"--user-data-dir={data_dir}")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-extensions")
        # 增加性能优化参数
        chrome_options.add_argument("--disable-dev-tools")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-save-password-bubble")
        # 添加内存和渲染相关优化
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-breakpad")
        chrome_options.add_argument("--disable-client-side-phishing-detection")
        chrome_options.add_argument("--disable-hang-monitor")
        chrome_options.add_argument("--disable-prompt-on-repost")
        chrome_options.add_argument("--ignore-certificate-errors")
        # 设置不等待页面加载完成
        chrome_options.page_load_strategy = 'eager'
        # 添加进程限制
        chrome_options.add_argument("--js-flags=--max-old-space-size=2048")
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--disable-crash-reporter")
        chrome_options.add_argument("--disable-in-process-stack-traces")
        # 禁用某些可能导致问题的功能
        chrome_options.add_argument("--disable-site-isolation-trials")
        print("启用无头模式运行Chrome")
    
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # 使用用户数据目录保持登录状态
    use_user_data_dir = not force_new_session and not config.get("HEADLESS", False)
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
        # 验证chromedriver是否可执行
        chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
        if not os.path.exists(chromedriver_path):
            print(f"ChromeDriver路径不存在: {chromedriver_path}")
            # 尝试查找chromedriver
            try:
                result = subprocess.run(['which', 'chromedriver'], 
                                        capture_output=True, 
                                        text=True, 
                                        check=False)
                if result.returncode == 0:
                    chromedriver_path = result.stdout.strip()
                    print(f"找到ChromeDriver: {chromedriver_path}")
            except Exception as e:
                print(f"查找ChromeDriver出错: {e}")
        
        # 设置服务超时参数
        service = Service(
            executable_path=chromedriver_path,
            log_path=os.devnull
        )
        
        monitor_api = config.get("MONITOR_API_RESPONSE", False)
        
        # 在启动前等待一段时间，确保系统资源可用
        time.sleep(1)
        
        if monitor_api:
            # 优化selenium-wire配置
            seleniumwire_options = {
                'disable_encoding': True,  # 禁用内容编码，以便能够读取响应体
                'suppress_connection_errors': True,  # 抑制连接错误
                'verify_ssl': False,  # 不验证SSL证书，避免某些HTTPS请求问题
                'request_storage': 'memory',  # 使用内存存储请求，提高性能
                'request_storage_max_size': 100,  # 最多存储100个请求，避免内存问题
                'connection_timeout': 120,  # 连接超时设置
                'connection_keep_alive': True,  # 保持连接
                'max_retries': 3  # 最大重试次数
            }
            
            # 设置请求过滤范围
            scopes = config.get("MONITOR_SCOPES", [r'.*pos\.meituan\.com.*'])
            
            print(f"使用ChromeDriver: {chromedriver_path}")
            
            # 再次检查目录权限
            tmp_dir = "/tmp/chrome_tmp"
            if not os.path.exists(tmp_dir):
                os.makedirs(tmp_dir, exist_ok=True)
                os.chmod(tmp_dir, 0o777)
            
            # 创建driver
            for attempt in range(3):  # 最多尝试3次
                try:
                    print(f"尝试启动Chrome (attempt {attempt+1}/3)")
                    driver = wire_webdriver.Chrome(
                        service=service,
                        options=chrome_options, 
                        seleniumwire_options=seleniumwire_options
                    )
                    
                    # 设置请求过滤
                    driver.scopes = scopes
                    # 设置脚本和页面加载超时
                    driver.set_script_timeout(30)
                    driver.set_page_load_timeout(60)
                    
                    print(f"已启用API监控，监控范围: {scopes}")
                    try:
                        browser_version = driver.capabilities['browserVersion']
                        driver_version = driver.capabilities['chrome']['chromedriverVersion'].split(' ')[0]
                        print(f"Chrome浏览器版本: {browser_version}")
                        print(f"ChromeDriver版本: {driver_version}")
                    except Exception as e:
                        print(f"获取浏览器版本信息失败: {e}")
                    
                    # 检查是否成功初始化
                    if driver:
                        print("Chrome浏览器已成功启动")
                        break
                except Exception as e:
                    print(f"启动Chrome失败 (attempt {attempt+1}/3): {e}")
                    if attempt < 2:  # 如果不是最后一次尝试
                        time.sleep(3)  # 等待一段时间后重试
                        try:
                            kill_chrome_processes()  # 清理可能的僵尸进程
                        except:
                            pass
                    else:
                        raise  # 最后一次尝试失败时抛出异常
            
        else:
            print(f"使用ChromeDriver: {chromedriver_path}")
            
            # 再次检查目录权限
            tmp_dir = "/tmp/chrome_tmp"
            if not os.path.exists(tmp_dir):
                os.makedirs(tmp_dir, exist_ok=True)
                os.chmod(tmp_dir, 0o777)
                
            # 使用标准webdriver，带重试
            for attempt in range(3):  # 最多尝试3次
                try:
                    print(f"尝试启动Chrome (attempt {attempt+1}/3)")
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    # 设置脚本和页面加载超时
                    driver.set_script_timeout(30)
                    driver.set_page_load_timeout(60)
                    
                    # 检查是否成功初始化
                    if driver:
                        print("Chrome浏览器已成功启动")
                        break
                except Exception as e:
                    print(f"启动Chrome失败 (attempt {attempt+1}/3): {e}")
                    if attempt < 2:  # 如果不是最后一次尝试
                        time.sleep(3)  # 等待一段时间后重试
                        try:
                            kill_chrome_processes()  # 清理可能的僵尸进程
                        except:
                            pass
                    else:
                        raise  # 最后一次尝试失败时抛出异常
            
        # 防止检测
        try:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        except Exception as e:
            print(f"设置反检测脚本时出错: {e}")
        
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
                chrome_options.add_argument("--window-size=1280,800")  # 减小窗口大小
                if config.get("HEADLESS", False):
                    chrome_options.add_argument("--headless=new")
                    # 添加解决DevToolsActivePort问题的参数
                    chrome_options.add_argument("--remote-debugging-port=9222")
                    chrome_options.add_argument("--disable-dev-shm-usage")
                    chrome_options.add_argument("--no-sandbox")
                    # 禁用GPU相关功能
                    chrome_options.add_argument("--disable-gpu")
                    chrome_options.add_argument("--disable-software-rasterizer")
                    # 临时目录权限问题
                    data_dir = "/tmp/chrome_tmp"
                    if not os.path.exists(data_dir):
                        os.makedirs(data_dir, exist_ok=True)
                        os.chmod(data_dir, 0o777)
                    chrome_options.add_argument(f"--user-data-dir={data_dir}")
                    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
                    chrome_options.add_argument("--disable-extensions")
                    # 增加性能优化参数
                    chrome_options.add_argument("--disable-dev-tools")
                    chrome_options.add_argument("--disable-infobars")
                    chrome_options.add_argument("--disable-notifications")
                    chrome_options.add_argument("--disable-popup-blocking")
                    chrome_options.add_argument("--disable-save-password-bubble")
                    # 添加内存和渲染相关优化
                    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
                    chrome_options.add_argument("--disable-breakpad")
                    chrome_options.add_argument("--disable-client-side-phishing-detection")
                    chrome_options.add_argument("--disable-hang-monitor")
                    chrome_options.add_argument("--disable-prompt-on-repost")
                    chrome_options.add_argument("--ignore-certificate-errors")
                    # 设置不等待页面加载完成
                    chrome_options.page_load_strategy = 'eager'
                    # 添加进程限制
                    chrome_options.add_argument("--js-flags=--max-old-space-size=2048")
                    chrome_options.add_argument("--memory-pressure-off")
                    chrome_options.add_argument("--disable-crash-reporter")
                    chrome_options.add_argument("--disable-in-process-stack-traces")
                    # 禁用某些可能导致问题的功能
                    chrome_options.add_argument("--disable-site-isolation-trials")
                
                chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option("useAutomationExtension", False)
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_argument("--log-level=3")
                chrome_options.add_argument("--silent")
                chrome_options.add_argument("--disable-logging")
                chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
                
                print("使用新会话模式启动Chrome...")
                
                # 设置服务
                chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
                service = Service(
                    executable_path=chromedriver_path,
                    log_path=os.devnull
                )
                
                monitor_api = config.get("MONITOR_API_RESPONSE", False)
                if monitor_api:
                    # 优化selenium-wire配置
                    seleniumwire_options = {
                        'disable_encoding': True,
                        'suppress_connection_errors': True,
                        'verify_ssl': False,
                        'request_storage': 'memory',
                        'request_storage_max_size': 100,
                        'connection_timeout': 120,
                        'connection_keep_alive': True,
                        'max_retries': 3
                    }
                    
                    # 设置请求过滤范围
                    scopes = config.get("MONITOR_SCOPES", [r'.*pos\.meituan\.com.*'])
                    
                    # 再次检查目录权限
                    tmp_dir = "/tmp/chrome_tmp"
                    if not os.path.exists(tmp_dir):
                        os.makedirs(tmp_dir, exist_ok=True)
                        os.chmod(tmp_dir, 0o777)
                    
                    # 创建driver，带重试
                    for attempt in range(3):  # 最多尝试3次
                        try:
                            print(f"尝试启动Chrome (attempt {attempt+1}/3)")
                            driver = wire_webdriver.Chrome(
                                service=service,
                                options=chrome_options,
                                seleniumwire_options=seleniumwire_options
                            )
                            
                            # 设置请求过滤
                            driver.scopes = scopes
                            # 设置脚本和页面加载超时
                            driver.set_script_timeout(30)
                            driver.set_page_load_timeout(60)
                            
                            # 检查是否成功初始化
                            if driver:
                                print("Chrome浏览器已成功启动")
                                break
                        except Exception as e:
                            print(f"启动Chrome失败 (attempt {attempt+1}/3): {e}")
                            if attempt < 2:  # 如果不是最后一次尝试
                                time.sleep(3)  # 等待一段时间后重试
                                try:
                                    kill_chrome_processes()  # 清理可能的僵尸进程
                                except:
                                    pass
                            else:
                                raise  # 最后一次尝试失败时抛出异常
                else:
                    # 再次检查目录权限
                    tmp_dir = "/tmp/chrome_tmp"
                    if not os.path.exists(tmp_dir):
                        os.makedirs(tmp_dir, exist_ok=True)
                        os.chmod(tmp_dir, 0o777)
                    
                    # 使用标准webdriver，带重试
                    for attempt in range(3):  # 最多尝试3次
                        try:
                            print(f"尝试启动Chrome (attempt {attempt+1}/3)")
                            driver = webdriver.Chrome(service=service, options=chrome_options)
                            # 设置脚本和页面加载超时
                            driver.set_script_timeout(30)
                            driver.set_page_load_timeout(60)
                            
                            # 检查是否成功初始化
                            if driver:
                                print("Chrome浏览器已成功启动")
                                break
                        except Exception as e:
                            print(f"启动Chrome失败 (attempt {attempt+1}/3): {e}")
                            if attempt < 2:  # 如果不是最后一次尝试
                                time.sleep(3)  # 等待一段时间后重试
                                try:
                                    kill_chrome_processes()  # 清理可能的僵尸进程
                                except:
                                    pass
                            else:
                                raise  # 最后一次尝试失败时抛出异常
                
                # 防止检测
                try:
                    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
                except Exception as e:
                    print(f"设置反检测脚本时出错: {e}")
                
                return driver
            except Exception as inner_e:
                raise Exception(f"无法启动Chrome: {inner_e}")
        else:
            # 其他类型的错误，抛出异常
            raise Exception(f"启动Chrome时出错: {e}") 
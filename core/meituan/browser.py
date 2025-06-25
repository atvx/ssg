from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver as wire_webdriver
import os
import time
import subprocess
import platform
import tempfile
import requests
import zipfile
import tarfile
import shutil
from pathlib import Path

from config.settings import settings
from utils.file_utils import kill_chrome_processes


def get_platform_info():
    """获取平台信息"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "windows":
        return "windows", "win32" if "32" in machine else "win64"
    elif system == "darwin":  # macOS
        return "mac", "mac-arm64" if "arm" in machine or "aarch64" in machine else "mac-x64"
    elif system == "linux":
        return "linux", "linux64"
    else:
        return system, machine


def get_chromedriver_default_paths():
    """获取不同平台下Chrome Driver的默认路径"""
    system, arch = get_platform_info()
    
    if system == "windows":
        return [
            os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google', 'Chrome', 'Application', 'chromedriver.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Google', 'Chrome', 'Application', 'chromedriver.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chromedriver.exe'),
            'chromedriver.exe',
            './chromedriver.exe'
        ]
    elif system == "mac":
        return [
            '/usr/local/bin/chromedriver',
            '/opt/homebrew/bin/chromedriver',  # Apple Silicon Mac
            '/usr/bin/chromedriver',
            './chromedriver',
            os.path.expanduser('~/bin/chromedriver')
        ]
    else:  # Linux
        return [
            '/usr/local/bin/chromedriver',
            '/usr/bin/chromedriver',
            './chromedriver',
            os.path.expanduser('~/bin/chromedriver')
        ]


def find_chromedriver():
    """查找Chrome Driver路径"""
    system, arch = get_platform_info()
    
    # 首先检查环境变量
    env_path = os.environ.get('CHROMEDRIVER_PATH')
    if env_path and os.path.exists(env_path):
        return env_path
    
    # 检查默认路径
    for path in get_chromedriver_default_paths():
        if os.path.exists(path):
            return path
    
    # 尝试使用系统命令查找
    try:
        if system == "windows":
            # Windows下使用where命令
            result = subprocess.run(['where', 'chromedriver'], 
                                  capture_output=True, text=True, check=False)
        else:
            # Unix系统使用which命令
            result = subprocess.run(['which', 'chromedriver'], 
                                  capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            path = result.stdout.strip()
            if os.path.exists(path):
                return path
    except Exception as e:
        print(f"查找ChromeDriver出错: {e}")
    
    return None


def download_chromedriver():
    """自动下载ChromeDriver"""
    system, arch = get_platform_info()
    
    try:
        # 获取Chrome版本
        chrome_version = get_chrome_version()
        if not chrome_version:
            print("无法检测Chrome版本，请手动安装ChromeDriver")
            return None
        
        # 根据平台确定下载URL
        if system == "windows":
            platform_name = "win32" if arch == "win32" else "win64"
            # 新API使用不同的命名
            platform_name_new = "win32" if arch == "win32" else "win64"
            filename = "chromedriver.exe"
        elif system == "mac":
            platform_name = "mac-arm64" if arch == "mac-arm64" else "mac-x64"
            # 新API使用不同的命名
            platform_name_new = "mac-arm64" if arch == "mac-arm64" else "mac-x64"
            filename = "chromedriver"
        else:  # Linux
            platform_name = "linux64"
            # 新API使用不同的命名
            platform_name_new = "linux64"
            filename = "chromedriver"
        
        # ChromeDriver下载URL（使用Chrome for Testing API）
        major_version = int(chrome_version.split('.')[0])
        
        print(f"正在获取ChromeDriver版本信息...")
        
        # Windows系统下直接使用指定版本的下载链接
        if system == "windows":
            # 直接使用与检测到的Chrome版本最接近的已知下载链接
            # 对于Chrome 137版本，使用137.0.7151.119的下载链接
            if major_version == 137:
                download_url = f"https://storage.googleapis.com/chrome-for-testing-public/137.0.7151.119/{platform_name_new}/chromedriver-{platform_name_new}.zip"
                driver_version = "137.0.7151.119"
            # 对于其他版本，尝试构建可能的下载链接
            elif major_version >= 115:
                # 尝试使用固定的次版本号构建URL
                possible_versions = [".0.7151.119", ".0.7258.2", ".0.7204.49", ".0.7103.113"]
                for v_suffix in possible_versions:
                    test_version = f"{major_version}{v_suffix}"
                    test_url = f"https://storage.googleapis.com/chrome-for-testing-public/{test_version}/{platform_name_new}/chromedriver-{platform_name_new}.zip"
                    try:
                        response = requests.head(test_url, timeout=5)
                        if response.status_code == 200:
                            download_url = test_url
                            driver_version = test_version
                            break
                    except:
                        continue
                else:
                    # 如果所有尝试都失败，回退到标准API查询
                    print("尝试预设版本失败，回退到标准下载流程")
                    return None
            else:
                # 对于较旧的Chrome版本，回退到旧API
                url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    print("无法获取ChromeDriver版本信息")
                    return None
                driver_version = response.text.strip()
                download_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_{platform_name}.zip"
        else:
            # 对于非Windows平台，保持原有的API查询逻辑
            # 对于Chrome 115+，使用新的Chrome for Testing API
            if major_version >= 115:
                api_url = f"https://googlechromelabs.github.io/chrome-for-testing/latest-patch-versions-per-milestone-with-downloads.json"
                try:
                    response = requests.get(api_url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        milestone_data = data.get('milestones', {}).get(str(major_version))
                        if milestone_data and 'downloads' in milestone_data:
                            chromedriver_downloads = milestone_data['downloads'].get('chromedriver', [])
                            # 查找匹配的平台
                            for download in chromedriver_downloads:
                                if download['platform'] == platform_name_new:
                                    download_url = download['url']
                                    driver_version = milestone_data['version']
                                    break
                            else:
                                raise Exception(f"未找到平台 {platform_name_new} 的ChromeDriver下载链接")
                        else:
                            raise Exception(f"未找到Chrome {major_version} 的ChromeDriver信息")
                    else:
                        raise Exception("无法获取Chrome for Testing API数据")
                except Exception as e:
                    print(f"使用新API失败: {e}，尝试旧API...")
                    # 回退到旧API
                    url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
                    response = requests.get(url, timeout=10)
                    if response.status_code != 200:
                        print("无法获取ChromeDriver版本信息")
                        return None
                    driver_version = response.text.strip()
                    download_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_{platform_name}.zip"
            else:
                # 对于Chrome 114及以下版本，使用旧API
                url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    print("无法获取ChromeDriver版本信息")
                    return None
                driver_version = response.text.strip()
                download_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_{platform_name}.zip"
        
        # 创建下载目录
        download_dir = os.path.join(tempfile.gettempdir(), "chromedriver_download")
        os.makedirs(download_dir, exist_ok=True)
        
        # 下载文件
        print(f"正在下载ChromeDriver {driver_version}...")
        zip_path = os.path.join(download_dir, "chromedriver.zip")
        response = requests.get(download_url, timeout=30)
        
        if response.status_code != 200:
            print(f"下载失败: {response.status_code}")
            return None
        
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        # 解压文件
        extract_dir = os.path.join(download_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # 找到解压后的chromedriver文件
        chromedriver_path = None
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.startswith('chromedriver'):
                    chromedriver_path = os.path.join(root, file)
                    break
            if chromedriver_path:
                break
        
        if not chromedriver_path:
            print("解压文件中未找到ChromeDriver")
            return None
        
        # 移动到合适的位置
        if system == "windows":
            target_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ChromeDriver')
        else:
            target_dir = os.path.expanduser('~/bin')
        
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, filename)
        
        shutil.copy2(chromedriver_path, target_path)
        
        # 在Unix系统上设置执行权限
        if system != "windows":
            os.chmod(target_path, 0o755)
        
        print(f"ChromeDriver已下载到: {target_path}")
        
        # 清理临时文件
        shutil.rmtree(download_dir, ignore_errors=True)
        
        return target_path
        
    except Exception as e:
        print(f"下载ChromeDriver失败: {e}")
        return None


def get_chrome_version():
    """获取Chrome版本"""
    system, arch = get_platform_info()
    
    try:
        if system == "windows":
            # Windows下通过注册表或文件版本获取
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
                version, _ = winreg.QueryValueEx(key, "version")
                winreg.CloseKey(key)
                return version
            except ImportError:
                # 如果winreg不可用（非Windows系统），跳过
                pass
            except:
                # 备选方案：检查Chrome可执行文件
                chrome_paths = [
                    os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
                    os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
                    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chrome.exe')
                ]
                for chrome_path in chrome_paths:
                    if os.path.exists(chrome_path):
                        result = subprocess.run([chrome_path, '--version'], 
                                              capture_output=True, text=True, check=False)
                        if result.returncode == 0:
                            return result.stdout.strip().split()[-1]
        elif system == "mac":
            # macOS
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if os.path.exists(chrome_path):
                result = subprocess.run([chrome_path, '--version'], 
                                      capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    return result.stdout.strip().split()[-1]
        else:
            # Linux
            result = subprocess.run(['google-chrome', '--version'], 
                                  capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return result.stdout.strip().split()[-1]
            
            # 备选命令
            result = subprocess.run(['chromium-browser', '--version'], 
                                  capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return result.stdout.strip().split()[-1]
                
    except Exception as e:
        print(f"获取Chrome版本失败: {e}")
    
    return None


def get_temp_dir():
    """获取跨平台的临时目录"""
    system, arch = get_platform_info()
    
    if system == "windows":
        temp_dir = os.path.join(tempfile.gettempdir(), "chrome_tmp")
    else:
        temp_dir = "/tmp/chrome_tmp"
    
    try:
        os.makedirs(temp_dir, exist_ok=True)
        # 只在非Windows系统设置权限
        if system != "windows":
            os.chmod(temp_dir, 0o777)
    except Exception as e:
        print(f"创建临时目录失败: {e}")
        # 回退到系统临时目录
        temp_dir = tempfile.gettempdir()
    
    return temp_dir


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
        # 使用跨平台临时目录
        data_dir = get_temp_dir()
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
        # 查找ChromeDriver路径
        chromedriver_path = find_chromedriver()
        
        if not chromedriver_path:
            print("未找到ChromeDriver，尝试自动下载...")
            chromedriver_path = download_chromedriver()
            
        if not chromedriver_path:
            print("无法找到或下载ChromeDriver，请手动安装")
            print("安装指南:")
            system, arch = get_platform_info()
            if system == "windows":
                print("1. 访问 https://chromedriver.chromium.org/downloads")
                print("2. 下载对应版本的chromedriver.exe")
                print("3. 将文件放在PATH环境变量目录或设置CHROMEDRIVER_PATH环境变量")
            elif system == "mac":
                print("1. 使用 Homebrew: brew install chromedriver")
                print("2. 或访问 https://chromedriver.chromium.org/downloads 手动下载")
            else:
                print("1. 使用包管理器: sudo apt-get install chromium-chromedriver")
                print("2. 或访问 https://chromedriver.chromium.org/downloads 手动下载")
            raise Exception("ChromeDriver未找到")
        
        print(f"使用ChromeDriver: {chromedriver_path}")
        
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
                'connection_keep_alive': True  # 保持连接
            }
            
            # 设置请求过滤范围
            scopes = config.get("MONITOR_SCOPES", [r'.*pos\.meituan\.com.*'])
            
            print(f"使用ChromeDriver: {chromedriver_path}")
            
            # 确保临时目录存在
            tmp_dir = get_temp_dir()
            
            # 创建driver
            print("尝试启动Chrome浏览器...")
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
        else:
            print(f"使用ChromeDriver: {chromedriver_path}")
            
            # 确保临时目录存在
            tmp_dir = get_temp_dir()
                
            # 使用标准webdriver
            print("尝试启动Chrome浏览器...")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            # 设置脚本和页面加载超时
            driver.set_script_timeout(30)
            driver.set_page_load_timeout(60)
            
        # 防止检测
        try:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        except Exception as e:
            print(f"设置反检测脚本时出错: {e}")
        
        print("Chrome浏览器已成功启动")
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
                    # 使用跨平台临时目录
                    data_dir = get_temp_dir()
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
                
                # 设置服务 - 使用跨平台ChromeDriver查找
                chromedriver_path = find_chromedriver()
                if not chromedriver_path:
                    chromedriver_path = download_chromedriver()
                if not chromedriver_path:
                    raise Exception("无法找到ChromeDriver")
                    
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
                        'connection_keep_alive': True
                    }
                    
                    # 设置请求过滤范围
                    scopes = config.get("MONITOR_SCOPES", [r'.*pos\.meituan\.com.*'])
                    
                    # 确保临时目录存在
                    tmp_dir = get_temp_dir()
                    
                    # 创建driver
                    print("尝试启动Chrome浏览器...")
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
                else:
                    # 确保临时目录存在
                    tmp_dir = get_temp_dir()
                    
                    # 使用标准webdriver
                    print("尝试启动Chrome浏览器...")
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    # 设置脚本和页面加载超时
                    driver.set_script_timeout(30)
                    driver.set_page_load_timeout(60)
                
                # 防止检测
                try:
                    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
                except Exception as e:
                    print(f"设置反检测脚本时出错: {e}")
                
                print("Chrome浏览器已成功启动")
                return driver
            except Exception as inner_e:
                raise Exception(f"无法启动Chrome: {inner_e}")
        else:
            # 其他类型的错误，抛出异常
            raise Exception(f"启动Chrome时出错: {e}") 
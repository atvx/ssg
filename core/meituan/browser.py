from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from seleniumwire import webdriver as wire_webdriver
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import os
import time
import subprocess
import platform
import tempfile
import requests
import zipfile
import tarfile
import shutil
import logging
from pathlib import Path
import io

from config.settings import settings
from utils.file_utils import kill_chrome_processes, force_kill_processes
from utils.chrome_cleanup import ChromeCleanup

logger = logging.getLogger(__name__)


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
    """查找ChromeDriver可执行文件路径"""
    # 获取系统默认路径
    paths = get_chromedriver_default_paths()
    
    # 检查路径是否存在
    for path in paths:
        if os.path.exists(path):
            logger.info(f"找到ChromeDriver: {path}")
            return path
    
    # 尝试从PATH环境变量中查找
    try:
        system, arch = get_platform_info()
        if system == "windows":
            result = subprocess.run(['where', 'chromedriver'], 
                                  capture_output=True, text=True, encoding='utf-8', errors='ignore', check=False)
            if result.returncode == 0:
                path = result.stdout.strip().split('\n')[0]
                if os.path.exists(path):
                    return path
        else:
            result = subprocess.run(['which', 'chromedriver'], 
                                  capture_output=True, text=True, encoding='utf-8', errors='ignore', check=False)
            if result.returncode == 0:
                path = result.stdout.strip()
                if os.path.exists(path):
                    return path
    except Exception as e:
        logger.warning(f"从PATH查找ChromeDriver时出错: {e}")
    
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
                                              capture_output=True, text=True, encoding='utf-8', errors='ignore', check=False)
                        if result.returncode == 0:
                            return result.stdout.strip().split()[-1]
        elif system == "mac":
            # macOS
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if os.path.exists(chrome_path):
                result = subprocess.run([chrome_path, '--version'], 
                                      capture_output=True, text=True, encoding='utf-8', errors='ignore', check=False)
                if result.returncode == 0:
                    return result.stdout.strip().split()[-1]
        else:
            # Linux
            result = subprocess.run(['google-chrome', '--version'], 
                                  capture_output=True, text=True, encoding='utf-8', errors='ignore', check=False)
            if result.returncode == 0:
                return result.stdout.strip().split()[-1]
            
            # 备选命令
            result = subprocess.run(['chromium-browser', '--version'], 
                                  capture_output=True, text=True, encoding='utf-8', errors='ignore', check=False)
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


def manual_download_edgedriver(version=None):
    """手动下载EdgeDriver
    
    Args:
        version: Edge浏览器版本，如果为None则尝试获取最新版本
        
    Returns:
        下载的EdgeDriver路径，如果下载失败则返回None
    """
    system, arch = get_platform_info()
    
    # 创建目录存放下载的EdgeDriver
    download_dir = os.path.join(os.path.expanduser("~"), ".wdm", "drivers", "edgedriver")
    os.makedirs(download_dir, exist_ok=True)
    
    # 确定平台对应的下载URL
    if system == "mac":
        if arch == "arm64":
            platform_name = "mac64_m1"
        else:
            platform_name = "mac64"
    elif system == "windows":
        platform_name = "win64"
    else:  # Linux
        platform_name = "linux64"
    
    # 如果没有指定版本，使用一个较新的稳定版本
    if not version:
        version = "114.0.1823.58"  # 使用一个相对稳定的版本
    
    # EdgeDriver下载URL
    download_url = f"https://msedgedriver.azureedge.net/{version}/edgedriver_{platform_name}.zip"
    
    try:
        logger.info(f"正在手动下载EdgeDriver {version}，URL: {download_url}")
        
        # 直接下载
        response = requests.get(download_url, timeout=30)
        response.raise_for_status()
        
        # 确定解压路径和可执行文件名
        if system == "windows":
            driver_name = "msedgedriver.exe"
        else:
            driver_name = "msedgedriver"
        
        driver_path = os.path.join(download_dir, driver_name)
        
        # 解压文件
        with ZipFile(io.BytesIO(response.content)) as zip_file:
            for item in zip_file.namelist():
                if item.endswith(driver_name):
                    with zip_file.open(item) as source, open(driver_path, "wb") as target:
                        shutil.copyfileobj(source, target)
        
        # 设置执行权限
        if system != "windows":
            os.chmod(driver_path, 0o755)
        
        logger.info(f"EdgeDriver已下载并解压到: {driver_path}")
        return driver_path
        
    except Exception as e:
        logger.error(f"手动下载EdgeDriver失败: {e}")
        return None


def init_edge_driver(config, force_new_session=False):
    """初始化Edge浏览器"""
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            # 清理已存在的进程
            if force_new_session or attempt > 0:
                logger.info("检测到Edge进程正在运行，等待退出...")
                force_kill_processes(['msedge', 'msedgedriver', 'Microsoft Edge'])
                time.sleep(3)
            
            # 配置Edge选项
            edge_options = EdgeOptions()
            
            # 设置用户数据目录
            user_data_dir = config.get("USER_DATA_DIR")
            if user_data_dir:
                if os.path.exists(user_data_dir):
                    logger.info(f"使用配置的用户数据目录: {user_data_dir}")
                    edge_options.add_argument(f"--user-data-dir={user_data_dir}")
                else:
                    logger.warning(f"用户数据目录不存在: {user_data_dir}")
            
            # 配置无头模式
            if config.get("HEADLESS", False):
                edge_options.add_argument("--headless")
                edge_options.add_argument("--disable-gpu")
                edge_options.add_argument("--no-sandbox")
                
                # 禁用可能导致问题的功能
                edge_options.add_argument("--disable-extensions")
                edge_options.add_argument("--disable-dev-tools")
                edge_options.add_argument("--disable-infobars")
                edge_options.add_argument("--disable-notifications")
                edge_options.add_argument("--disable-popup-blocking")
                edge_options.add_argument("--disable-save-password-bubble")
                edge_options.add_argument("--disable-features=VizDisplayCompositor")
                edge_options.add_argument("--disable-site-isolation-trials")
                edge_options.add_argument("--disable-backgrounding-occluded-windows")
                edge_options.add_argument("--disable-breakpad")
                edge_options.add_argument("--disable-client-side-phishing-detection")
                edge_options.add_argument("--disable-hang-monitor")
                edge_options.add_argument("--disable-prompt-on-repost")
                edge_options.add_argument("--ignore-certificate-errors")
                
                # 内存相关优化
                edge_options.add_argument("--js-flags=--max-old-space-size=2048")
                edge_options.add_argument("--memory-pressure-off")
                edge_options.add_argument("--disable-crash-reporter")
                edge_options.add_argument("--disable-in-process-stack-traces")
                
                # 加载策略调整
                edge_options.page_load_strategy = 'eager'
            
            # 设置通用的用户代理和反检测
            edge_options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            edge_options.add_experimental_option("useAutomationExtension", False)
            edge_options.add_argument("--disable-blink-features=AutomationControlled")
            
            # 减少日志输出
            edge_options.add_argument("--log-level=3")
            edge_options.add_argument("--silent")
            edge_options.add_argument("--disable-logging")
            edge_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
            
            # 获取EdgeDriver路径
            driver_path = None
            
            # 首先查找本地已有的EdgeDriver
            driver_path = find_edgedriver()
            
            # 如果找不到本地Driver，尝试使用webdriver_manager下载
            if not driver_path:
                try:
                    logger.info("正在检查并下载最新的EdgeDriver...")
                    # 设置超时时间，避免长时间等待
                    os.environ['WDM_TIMEOUT'] = '30'
                    os.environ['WDM_SSL_VERIFY'] = '0'
                    
                    driver_path = EdgeChromiumDriverManager().install()
                    logger.info(f"WebDriver Manager下载的EdgeDriver: {driver_path}")
                except Exception as e:
                    logger.warning(f"自动下载EdgeDriver失败: {e}")
                    logger.info("尝试手动下载EdgeDriver...")
                    
                    # 尝试手动下载
                    driver_path = manual_download_edgedriver()
            
            # 如果仍然无法获取EdgeDriver路径，则抛出异常
            if not driver_path:
                raise Exception("无法获取EdgeDriver路径，请手动下载并安装EdgeDriver")
            
            logger.info(f"使用EdgeDriver: {driver_path}")
            
            # 设置服务
            service = EdgeService(executable_path=driver_path)
            
            monitor_api = config.get("MONITOR_API_RESPONSE", False)
            
            # 启动前多等待一段时间，确保系统资源可用
            time.sleep(2)
            
            if monitor_api:
                # 使用全局配置的selenium-wire选项
                seleniumwire_options = settings.SELENIUM_WIRE_OPTIONS.copy()
                
                # 设置请求过滤范围
                scopes = config.get("MONITOR_SCOPES", [r'.*pos\.meituan\.com.*'])
                
                # 创建driver
                logger.info("尝试启动Edge浏览器...")
                driver = wire_webdriver.Edge(
                    service=service,
                    options=edge_options, 
                    seleniumwire_options=seleniumwire_options
                )
                
                # 设置请求过滤
                driver.scopes = scopes
                
                # 降低超时时间以更快检测问题
                driver.set_script_timeout(20)
                driver.set_page_load_timeout(45)
                
                logger.info(f"已启用API监控，监控范围: {scopes}")
            else:
                # 使用标准webdriver
                logger.info("尝试启动Edge浏览器...")
                driver = webdriver.Edge(service=service, options=edge_options)
                
                # 降低超时时间
                driver.set_script_timeout(20)
                driver.set_page_load_timeout(45)
            
            # 显示版本信息
            try:
                browser_version = driver.capabilities['browserVersion']
                driver_version = driver.capabilities.get('msedge', {}).get('msedgedriverVersion', 'Unknown').split(' ')[0]
                logger.info(f"Edge浏览器版本: {browser_version}")
                logger.info(f"EdgeDriver版本: {driver_version}")
            except Exception as e:
                logger.warning(f"获取浏览器版本信息失败: {e}")
            
            # 防止检测
            try:
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
                
                # 额外的防检测脚本
                driver.execute_script("""
                    // 隐藏自动化相关特征
                    Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 10});
                    Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
                    Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                    
                    // 覆盖一些可能被用于检测的属性
                    if (window.Notification) window.Notification.permission = 'default';
                    """)
            except Exception as e:
                logger.warning(f"设置反检测脚本时出错: {e}")
            
            logger.info("Edge浏览器已成功启动")
            return driver
            
        except Exception as e:
            error_message = str(e).lower()
            logger.error(f"浏览器启动失败 (尝试 {attempt+1}/{max_attempts}): {error_message}")
            
            if attempt < max_attempts - 1:
                logger.info("正在清理并重试...")
                force_kill_processes(['msedge', 'msedgedriver', 'Microsoft Edge'])
                time.sleep(5)  # 等待更长时间
            else:
                raise Exception(f"多次尝试后仍无法启动浏览器: {e}")
    
    # 如果所有尝试都失败
    raise Exception("无法启动Edge浏览器，已达到最大尝试次数") 


def get_edge_default_paths():
    """获取不同平台下Edge Driver的默认路径"""
    system, arch = get_platform_info()
    
    if system == "windows":
        return [
            os.path.join(os.environ.get('PROGRAMFILES', ''), 'Microsoft', 'Edge', 'Application', 'msedgedriver.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Microsoft', 'Edge', 'Application', 'msedgedriver.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Edge', 'Application', 'msedgedriver.exe'),
            'msedgedriver.exe',
            './msedgedriver.exe'
        ]
    elif system == "mac":
        return [
            '/usr/local/bin/msedgedriver',
            '/opt/homebrew/bin/msedgedriver',  # Apple Silicon Mac
            '/usr/bin/msedgedriver',
            './msedgedriver',
            os.path.expanduser('~/bin/msedgedriver')
        ]
    else:  # Linux
        return [
            '/usr/local/bin/msedgedriver',
            '/usr/bin/msedgedriver',
            './msedgedriver',
            os.path.expanduser('~/bin/msedgedriver')
        ]


def find_edgedriver():
    """查找EdgeDriver可执行文件路径"""
    # 获取系统默认路径
    paths = get_edge_default_paths()
    
    # 检查路径是否存在
    for path in paths:
        if os.path.exists(path):
            logger.info(f"找到EdgeDriver: {path}")
            return path
    
    # 尝试从PATH环境变量中查找
    try:
        system, arch = get_platform_info()
        if system == "windows":
            result = subprocess.run(['where', 'msedgedriver'], 
                                  capture_output=True, text=True, encoding='utf-8', errors='ignore', check=False)
            if result.returncode == 0:
                path = result.stdout.strip().split('\n')[0]
                if os.path.exists(path):
                    return path
        else:
            result = subprocess.run(['which', 'msedgedriver'], 
                                  capture_output=True, text=True, encoding='utf-8', errors='ignore', check=False)
            if result.returncode == 0:
                path = result.stdout.strip()
                if os.path.exists(path):
                    return path
    except Exception as e:
        logger.warning(f"从PATH查找EdgeDriver时出错: {e}")
    
    return None 
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os

from config.settings import settings


def get_browser():
    """获取配置好的Selenium浏览器实例"""
    chrome_options = Options()
    
    # 设置用户数据目录
    user_data_dir = os.path.abspath(settings.CHROME_USER_DATA_DIR)
    os.makedirs(user_data_dir, exist_ok=True)
    chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    
    # 无头模式配置
    if settings.HEADLESS:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
    
    # 通用配置
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-extensions")
    
    # 创建WebDriver实例
    service = Service(ChromeDriverManager().install())
    browser = webdriver.Chrome(service=service, options=chrome_options)
    
    # 设置隐式等待时间
    browser.implicitly_wait(10)
    
    return browser

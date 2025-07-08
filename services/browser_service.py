from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
import os
import logging

from config.settings import settings
from core.meituan.browser import find_edgedriver

logger = logging.getLogger(__name__)

def get_browser():
    """获取配置好的Selenium浏览器实例"""
    edge_options = EdgeOptions()
    
    # 设置用户数据目录
    user_data_dir = os.path.abspath(settings.EDGE_USER_DATA_DIR)
    os.makedirs(user_data_dir, exist_ok=True)
    edge_options.add_argument(f"user-data-dir={user_data_dir}")
    
    # 无头模式配置
    if settings.HEADLESS:
        edge_options.add_argument("--headless")
        edge_options.add_argument("--no-sandbox")
        edge_options.add_argument("--disable-dev-shm-usage")
        edge_options.add_argument("--disable-gpu")
    
    # 通用配置
    edge_options.add_argument("--window-size=1920,1080")
    edge_options.add_argument("--disable-notifications")
    edge_options.add_argument("--disable-popup-blocking")
    edge_options.add_argument("--disable-extensions")
    
    # 查找EdgeDriver路径
    edgedriver_path = find_edgedriver()
    if not edgedriver_path:
        logger.error("无法找到EdgeDriver，请确保已正确安装")
        raise Exception("EdgeDriver未找到")
    
    logger.info(f"使用EdgeDriver: {edgedriver_path}")
    
    # 创建WebDriver实例
    service = EdgeService(executable_path=edgedriver_path)
    browser = webdriver.Edge(service=service, options=edge_options)
    
    # 设置隐式等待时间
    browser.implicitly_wait(10)
    
    return browser

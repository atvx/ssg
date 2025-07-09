#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Selenium配置脚本 - 用于Docker环境中的Selenium设置优化
"""

import os
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("selenium_setup")

def ensure_edge_dirs():
    """确保Edge相关目录存在并具有正确权限"""
    dirs = [
        "/app/edge_user_data",
        "/tmp/edge_tmp",
        "/var/run/edge"
    ]
    for dir_path in dirs:
        path = Path(dir_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建目录: {dir_path}")
        
        # 设置权限
        os.chmod(dir_path, 0o777)
        logger.info(f"设置权限: {dir_path}")


def check_browser_binaries():
    """检查浏览器可执行文件是否存在"""
    edge_paths = [
        "/usr/bin/microsoft-edge",
        "/usr/bin/microsoft-edge-stable",
        "/usr/bin/microsoft-edge-dev",
        "/usr/bin/microsoft-edge-beta"
    ]
    
    edge_found = False
    for path in edge_paths:
        if os.path.exists(path):
            logger.info(f"找到Edge浏览器: {path}")
            edge_found = True
            break
    
    if not edge_found:
        logger.warning("未找到Edge浏览器，可能需要安装")
    
    # EdgeDriver现在通过webdriver-manager自动管理
    logger.info("EdgeDriver将通过webdriver-manager自动下载和管理")


def setup_edge_preferences():
    """设置Edge首选项以优化性能和内存使用"""
    user_data_dir = "/app/edge_user_data"
    default_dir = os.path.join(user_data_dir, "Default")
    
    # 确保目录存在
    os.makedirs(default_dir, exist_ok=True)
    
    # 创建首选项文件
    prefs_file = os.path.join(default_dir, "Preferences")
    
    # 首选项内容 - 优化内存使用和性能
    prefs = {
        "profile": {
            "default_content_setting_values": {
                "images": 2,  # 禁用图片加载
                "plugins": 2,  # 禁用插件
                "popups": 2,  # 禁用弹窗
                "geolocation": 2,  # 禁用地理位置
                "notifications": 2,  # 禁用通知
                "auto_select_certificate": 2,  # 禁用自动选择证书
                "fullscreen": 2,  # 禁用全屏
                "mouselock": 2,  # 禁用鼠标锁定
                "mixed_script": 2,  # 禁用混合脚本
                "media_stream": 2,  # 禁用媒体流
                "media_stream_mic": 2,  # 禁用麦克风
                "media_stream_camera": 2,  # 禁用摄像头
                "protocol_handlers": 2,  # 禁用协议处理程序
                "ppapi_broker": 2,  # 禁用PPAPI代理
                "automatic_downloads": 2,  # 禁用自动下载
                "midi_sysex": 2,  # 禁用MIDI
                "push_messaging": 2,  # 禁用推送消息
                "ssl_cert_decisions": 2,  # 禁用SSL证书决策
                "metro_switch_to_desktop": 2,  # 禁用Metro切换到桌面
                "protected_media_identifier": 2,  # 禁用受保护的媒体标识符
                "app_banner": 2,  # 禁用应用横幅
                "site_engagement": 2,  # 禁用站点参与
                "durable_storage": 2  # 禁用持久存储
            },
            "password_manager_enabled": False
        },
        "translate_blocked_languages": ["zh-CN"],
        "translate": {"enabled": False},
        "download": {
            "prompt_for_download": True,
            "directory_upgrade": True,
            "extensions_to_open": ""
        },
        "browser": {
            "custom_chrome_frame": False,
            "show_home_button": False,
            "check_default_browser": False,
            "clear_data": {
                "browsing_history": True,
                "cache": True,
                "cookies": True,
                "download_history": True,
                "form_data": True,
                "hosted_apps_data": True,
                "passwords": True
            },
            "clear_lso_data_enabled": True,
            "pepper_flash_settings_enabled": False
        },
        "net": {
            "network_prediction_options": 2
        },
        "search": {
            "suggest_enabled": False
        },
        "dns_prefetching": {
            "enabled": False
        },
        "safebrowsing": {
            "enabled": False,
            "scout_group_selected": False
        },
        "backup": {
            "sync_enabled": False
        },
        "credentials_enable_service": False,
        "credentials_enable_autosignin": False
    }
    
    # 写入首选项文件
    with open(prefs_file, 'w', encoding='utf-8') as f:
        json.dump(prefs, f, indent=4)
    
    logger.info(f"已创建Edge首选项文件: {prefs_file}")

def setup_selenium_env():
    """设置Selenium环境变量"""
    # 设置Edge浏览器环境变量
    os.environ["EDGE_BIN"] = "/usr/bin/microsoft-edge"
    os.environ["EDGE_PATH"] = "/usr/bin/microsoft-edge"
    os.environ["SELENIUM_BROWSER_BINARY"] = "/usr/bin/microsoft-edge"
    os.environ["SELENIUM_BROWSER"] = "edge"
    os.environ["BROWSER_TYPE"] = "edge"
    os.environ["USE_EDGE"] = "true"
    
    # 设置webdriver-manager环境变量
    os.environ["WDM_LOG_LEVEL"] = "0"
    os.environ["WDM_SSL_VERIFY"] = "0"
    os.environ["WDM_LOCAL"] = "1"
    os.environ["WDM_PRINT_FIRST_LINE"] = "False"
    
    # 设置Edge启动选项
    os.environ["EDGE_OPTIONS"] = "--no-sandbox --disable-dev-shm-usage --disable-gpu --headless=new --disable-software-rasterizer --disable-extensions --window-size=1920,1080 --single-process --disable-background-networking --ignore-certificate-errors --disable-infobars --disable-dev-tools"
    
    logger.info("已设置Selenium和webdriver-manager环境变量")

def main():
    """主函数"""
    logger.info("启动Selenium环境设置...")
    
    # 确保Edge目录存在
    ensure_edge_dirs()
    
    # 检查浏览器可执行文件
    check_browser_binaries()
    
    # 设置Edge首选项
    setup_edge_preferences()
    
    # 设置Selenium环境变量
    setup_selenium_env()
    
    logger.info("Selenium环境设置完成")

if __name__ == "__main__":
    main() 
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

def ensure_chrome_dirs():
    """确保Chrome相关目录存在并具有正确权限"""
    dirs = [
        "/app/chrome_user_data",
        "/tmp/chrome_tmp",
        "/var/run/chrome"
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
    """检查浏览器可执行文件是否存在并可执行"""
    binaries = [
        ("/usr/bin/google-chrome", "Google Chrome"),
        ("/usr/local/bin/chromedriver", "ChromeDriver"),
        ("/usr/bin/firefox-esr", "Firefox ESR"),
        ("/usr/local/bin/geckodriver", "GeckoDriver")
    ]
    
    for binary_path, name in binaries:
        if os.path.exists(binary_path):
            if os.access(binary_path, os.X_OK):
                # 获取版本信息
                try:
                    if "chrome" in binary_path:
                        version_cmd = [binary_path, "--version"]
                    elif "firefox" in binary_path:
                        version_cmd = [binary_path, "--version"]
                    elif "driver" in binary_path:
                        version_cmd = [binary_path, "--version"]
                    
                    result = subprocess.run(
                        version_cmd, 
                        capture_output=True, 
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        version = result.stdout.strip()
                        logger.info(f"{name} 可用: {version}")
                    else:
                        logger.warning(f"{name} 可执行但无法获取版本")
                except Exception as e:
                    logger.warning(f"无法获取 {name} 版本: {str(e)}")
            else:
                logger.warning(f"{name} 存在但不可执行: {binary_path}")
                try:
                    os.chmod(binary_path, 0o755)
                    logger.info(f"已修复 {name} 权限")
                except Exception as e:
                    logger.error(f"无法修复 {name} 权限: {str(e)}")
        else:
            logger.error(f"{name} 不存在: {binary_path}")

def setup_chrome_preferences():
    """设置Chrome首选项以优化性能和内存使用"""
    user_data_dir = "/app/chrome_user_data"
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
    
    logger.info(f"已创建Chrome首选项文件: {prefs_file}")

def setup_selenium_env():
    """设置Selenium环境变量"""
    # 设置Chrome和WebDriver环境变量
    os.environ["CHROME_BIN"] = "/usr/bin/google-chrome"
    os.environ["CHROMIUM_PATH"] = "/usr/bin/google-chrome"
    os.environ["CHROMEDRIVER_PATH"] = "/usr/local/bin/chromedriver"
    os.environ["SELENIUM_DRIVER_PATH"] = "/usr/local/bin/chromedriver"
    os.environ["SELENIUM_BROWSER_BINARY"] = "/usr/bin/google-chrome"
    
    # 设置Chrome启动选项
    os.environ["CHROME_OPTIONS"] = "--no-sandbox --disable-dev-shm-usage --disable-gpu --headless=new --disable-software-rasterizer --disable-extensions --window-size=1920,1080 --single-process --disable-background-networking --ignore-certificate-errors --disable-infobars --disable-dev-tools"
    
    logger.info("已设置Selenium环境变量")

def main():
    """主函数"""
    logger.info("启动Selenium环境设置...")
    
    # 确保Chrome目录存在
    ensure_chrome_dirs()
    
    # 检查浏览器可执行文件
    check_browser_binaries()
    
    # 设置Chrome首选项
    setup_chrome_preferences()
    
    # 设置Selenium环境变量
    setup_selenium_env()
    
    logger.info("Selenium环境设置完成")

if __name__ == "__main__":
    main() 
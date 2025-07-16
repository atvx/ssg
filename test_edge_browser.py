#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 导入浏览器初始化函数
from core.meituan.browser import init_edge_driver, manual_download_edgedriver, find_edgedriver

# 主测试函数
def test_browser_initialization():
    """测试浏览器初始化功能"""
    
    print("\n======= Edge浏览器测试 =======")
    
    # 先尝试查找本地EdgeDriver
    print("\n1. 测试查找本地EdgeDriver")
    local_driver_path = find_edgedriver()
    if local_driver_path:
        print(f"✅ 本地找到EdgeDriver: {local_driver_path}")
    else:
        print("⚠️ 未找到本地EdgeDriver")
    
    # 测试手动下载
    print("\n2. 测试手动下载EdgeDriver")
    try:
        driver_path = manual_download_edgedriver()
        if driver_path:
            print(f"✅ 手动下载EdgeDriver成功: {driver_path}")
        else:
            print("❌ 手动下载EdgeDriver失败")
    except Exception as e:
        print(f"❌ 手动下载EdgeDriver出错: {e}")
    
    # 测试浏览器初始化
    print("\n3. 测试Edge浏览器初始化")
    config = {
        "USER_DATA_DIR": os.path.join(os.getcwd(), "edge_user_data"),
        "HEADLESS": True,
        "MONITOR_API_RESPONSE": False
    }
    
    try:
        driver = init_edge_driver(config)
        print("✅ Edge浏览器初始化成功")
        
        # 加载测试页面
        print("\n4. 测试页面加载")
        driver.get("https://www.baidu.com")
        print(f"✅ 成功加载页面: {driver.title}")
        
        # 关闭浏览器
        driver.quit()
        print("✅ 浏览器成功关闭")
        
        return True
    except Exception as e:
        print(f"❌ 浏览器初始化失败: {e}")
        return False

# 执行测试
if __name__ == "__main__":
    success = test_browser_initialization()
    if success:
        print("\n✅ 测试通过 - Edge浏览器初始化功能正常")
        sys.exit(0)
    else:
        print("\n❌ 测试失败 - 请检查错误信息并修复问题")
        sys.exit(1) 
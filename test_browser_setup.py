#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器配置测试脚本
用于验证跨平台浏览器自动化功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from core.meituan.browser import (
    get_platform_info, 
    find_chromedriver, 
    get_chrome_version,
    get_temp_dir,
    init_chrome_driver
)


def test_platform_detection():
    """测试平台检测功能"""
    print("=== 平台检测测试 ===")
    try:
        system, arch = get_platform_info()
        print(f"✅ 检测到操作系统: {system}")
        print(f"✅ 检测到架构: {arch}")
        return True
    except Exception as e:
        print(f"❌ 平台检测失败: {e}")
        return False


def test_chrome_version():
    """测试Chrome版本检测"""
    print("\n=== Chrome版本检测测试 ===")
    try:
        version = get_chrome_version()
        if version:
            print(f"✅ 检测到Chrome版本: {version}")
            return True
        else:
            print("⚠️ 未检测到Chrome浏览器")
            return False
    except Exception as e:
        print(f"❌ Chrome版本检测失败: {e}")
        return False


def test_chromedriver_detection():
    """测试ChromeDriver检测功能"""
    print("\n=== ChromeDriver检测测试 ===")
    try:
        chromedriver_path = find_chromedriver()
        if chromedriver_path:
            print(f"✅ 找到ChromeDriver: {chromedriver_path}")
            return True
        else:
            print("⚠️ 未找到ChromeDriver，稍后会尝试自动下载")
            return False
    except Exception as e:
        print(f"❌ ChromeDriver检测失败: {e}")
        return False


def test_temp_directory():
    """测试临时目录创建"""
    print("\n=== 临时目录测试 ===")
    try:
        temp_dir = get_temp_dir()
        print(f"✅ 临时目录: {temp_dir}")
        
        # 检查目录是否真正存在
        if os.path.exists(temp_dir):
            print(f"✅ 临时目录已创建并可访问")
            return True
        else:
            print(f"❌ 临时目录创建失败")
            return False
    except Exception as e:
        print(f"❌ 临时目录测试失败: {e}")
        return False


def test_browser_initialization():
    """测试浏览器初始化"""
    print("\n=== 浏览器初始化测试 ===")
    
    # 从配置中读取无头模式设置
    from config.settings import settings
    headless = settings.HEADLESS
    print(f"配置中的无头模式设置: HEADLESS={headless}")
    
    # 测试配置
    config = {
        "HEADLESS": headless,  # 使用配置中的无头模式设置
        "MONITOR_API_RESPONSE": False
    }
    
    try:
        print("正在初始化Edge浏览器...")
        driver = init_chrome_driver(config)
        
        if driver:
            print("✅ Edge浏览器启动成功")
            
            # 简单页面加载测试
            try:
                driver.get("https://www.google.com")
                title = driver.title
                print(f"✅ 页面加载成功: {title}")
                
                # 获取浏览器信息
                try:
                    browser_version = driver.capabilities.get('browserVersion', 'Unknown')
                    edge_version = driver.capabilities.get('msedge', {}).get('msedgedriverVersion', 'Unknown')
                    print(f"✅ 浏览器版本: {browser_version}")
                    print(f"✅ EdgeDriver版本: {edge_version}")
                except:
                    print("⚠️ 无法获取版本信息")
                
            except Exception as e:
                print(f"⚠️ 页面加载失败: {e}")
            
            # 关闭浏览器
            try:
                driver.quit()
                print("✅ 浏览器已成功关闭")
                return True
            except Exception as e:
                print(f"⚠️ 浏览器关闭时出现问题: {e}")
                return True  # 启动成功就算测试通过
        else:
            print("❌ 浏览器启动失败")
            return False
    except Exception as e:
        print(f"❌ 浏览器初始化失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 开始浏览器配置测试\n")
    
    # 执行所有测试
    tests = [
        ("平台检测", test_platform_detection),
        ("Chrome版本检测", test_chrome_version),
        ("ChromeDriver检测", test_chromedriver_detection),
        ("临时目录", test_temp_directory),
        ("浏览器初始化", test_browser_initialization)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试 '{test_name}' 执行异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果汇总
    print("\n" + "="*50)
    print("📊 测试结果汇总")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print("-"*50)
    print(f"总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！浏览器配置正常")
        return 0
    elif passed >= total - 1:  # 允许一个测试失败
        print("⚠️ 大部分测试通过，浏览器基本可用")
        return 0
    else:
        print("💥 多项测试失败，请检查配置")
        print("📖 请参考 BROWSER_SETUP.md 进行故障排除")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 
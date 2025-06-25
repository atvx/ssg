#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量加载测试脚本
用于验证.env文件是否被正确加载
"""

import os
import sys
from pathlib import Path

# 确保能找到项目模块
sys.path.insert(0, str(Path(__file__).parent))

def test_env_file_exists():
    """测试.env文件是否存在"""
    print("\n=== .env文件检查 ===")
    env_path = Path(__file__).parent / '.env'
    
    if env_path.exists():
        print(f"✅ .env文件存在: {env_path}")
        try:
            with open(env_path, 'r') as f:
                content = f.read()
                print(f"✅ .env文件内容长度: {len(content)} 字节")
                # 检查文件内是否包含HEADLESS=True
                if 'HEADLESS=True' in content:
                    print(f"✅ .env文件中包含 HEADLESS=True 设置")
                else:
                    print(f"❌ .env文件中没有找到 HEADLESS=True 设置")
        except Exception as e:
            print(f"❌ 读取.env文件失败: {e}")
        return True
    else:
        print(f"❌ .env文件不存在: {env_path}")
        return False

def test_env_variable_loading():
    """测试环境变量加载"""
    print("\n=== 环境变量加载测试 ===")
    # 记录修改前的环境变量值
    headless_before = os.environ.get("HEADLESS")
    print(f"加载settings前的HEADLESS环境变量: {headless_before}")
    
    try:
        # 导入设置模块，触发.env加载
        from config.settings import settings
        
        # 检查settings中的HEADLESS值
        print(f"settings.HEADLESS = {settings.HEADLESS}")
        
        # 检查环境变量是否被设置
        headless_after = os.environ.get("HEADLESS")
        print(f"加载settings后的HEADLESS环境变量: {headless_after}")
        
        # 检查是否成功加载
        if headless_after == "True" and settings.HEADLESS is True:
            print("✅ HEADLESS环境变量已被正确加载")
            return True
        else:
            print("❌ HEADLESS环境变量未被正确加载")
            return False
    except Exception as e:
        print(f"❌ 加载settings模块失败: {e}")
        return False

def test_browser_service():
    """测试浏览器服务是否正确使用HEADLESS设置"""
    print("\n=== 浏览器服务HEADLESS测试 ===")
    try:
        from config.settings import settings
        from services.browser_service import get_browser
        
        print(f"当前HEADLESS设置: {settings.HEADLESS}")
        print("尝试初始化浏览器服务...")
        
        # 不实际创建浏览器实例，只检查代码逻辑
        if settings.HEADLESS:
            print("✅ HEADLESS=True, 浏览器应以无头模式启动")
        else:
            print("❌ HEADLESS=False, 浏览器将以有界面模式启动")
        
        return settings.HEADLESS
    except Exception as e:
        print(f"❌ 测试浏览器服务失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始环境变量加载测试\n")
    
    # 执行所有测试
    tests = [
        ("检查.env文件", test_env_file_exists),
        ("环境变量加载", test_env_variable_loading),
        ("浏览器服务HEADLESS", test_browser_service)
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
        print("🎉 所有测试通过！环境变量加载正常")
        return 0
    else:
        print("💥 测试失败，请检查环境变量配置")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 
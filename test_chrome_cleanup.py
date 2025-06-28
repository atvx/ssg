#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chrome清理工具测试脚本
"""

import os
import sys
import logging
import tempfile
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_chrome_files():
    """创建模拟的Chrome文件用于测试"""
    test_dirs = [
        "./test_chrome_user_data",
        "./test_chrome_tmp"
    ]
    
    # 创建测试文件
    test_files = [
        "test_chrome_user_data/SingletonLock",
        "test_chrome_user_data/SingletonCookie",
        "test_chrome_user_data/SingletonSocket",
        "test_chrome_user_data/Default/Preferences-journal",
        "test_chrome_user_data/Default/Cache/Cache_Data/index-test",
        "test_chrome_user_data/Default/Cache/Cache_Data/data_0",
        "test_chrome_tmp/SingletonLock",
        "test_chrome_tmp/Default/Cache/Cache_Data/index-test"
    ]
    
    logger.info("创建测试Chrome文件...")
    created_files = []
    
    for file_path in test_files:
        try:
            # 创建目录
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 创建文件
            with open(file_path, 'w') as f:
                f.write("test chrome file")
            
            created_files.append(file_path)
            logger.debug(f"创建测试文件: {file_path}")
            
        except Exception as e:
            logger.error(f"创建测试文件失败 {file_path}: {e}")
    
    logger.info(f"创建了 {len(created_files)} 个测试文件")
    return created_files

def test_chrome_cleanup():
    """测试Chrome清理功能"""
    logger.info("=== 开始Chrome清理工具测试 ===")
    
    try:
        # 1. 创建测试文件
        test_files = create_test_chrome_files()
        
        # 验证文件存在
        existing_before = [f for f in test_files if os.path.exists(f)]
        logger.info(f"测试前存在的文件数量: {len(existing_before)}")
        
        # 2. 导入并使用Chrome清理工具
        from utils.chrome_cleanup import ChromeCleanup
        
        # 创建清理器实例
        cleaner = ChromeCleanup()
        
        # 测试进程检测
        logger.info("测试Chrome进程检测...")
        is_running = cleaner.is_chrome_running()
        logger.info(f"Chrome进程状态: {'运行中' if is_running else '未运行'}")
        
        # 3. 执行自定义清理（清理测试目录）
        logger.info("开始清理测试文件...")
        
        # 清理测试目录
        test_directories = ["./test_chrome_user_data", "./test_chrome_tmp"]
        for directory in test_directories:
            if os.path.exists(directory):
                cleaner.cleanup_chrome_directory(directory)
        
        # 4. 验证清理结果
        time.sleep(0.5)  # 等待清理完成
        
        existing_after = [f for f in test_files if os.path.exists(f)]
        cleaned_files = len(existing_before) - len(existing_after)
        
        logger.info(f"测试后存在的文件数量: {len(existing_after)}")
        logger.info(f"成功清理的文件数量: {cleaned_files}")
        
        # 5. 显示清理结果
        if existing_after:
            logger.info("未清理的文件:")
            for file_path in existing_after:
                logger.info(f"  - {file_path}")
        
        # 6. 清理测试目录
        logger.info("清理测试目录...")
        import shutil
        for directory in test_directories:
            if os.path.exists(directory):
                try:
                    shutil.rmtree(directory)
                    logger.debug(f"已删除测试目录: {directory}")
                except Exception as e:
                    logger.warning(f"删除测试目录失败 {directory}: {e}")
        
        # 7. 测试完整清理功能
        logger.info("测试完整清理功能...")
        try:
            cleaner.cleanup_all()
            logger.info("完整清理测试通过")
        except Exception as e:
            logger.error(f"完整清理测试失败: {e}")
        
        logger.info("=== Chrome清理工具测试完成 ===")
        
        # 返回测试结果
        return {
            "total_files": len(test_files),
            "files_before": len(existing_before),
            "files_after": len(existing_after),
            "cleaned_count": cleaned_files,
            "success": cleaned_files > 0
        }
        
    except ImportError as e:
        logger.error(f"导入Chrome清理工具失败: {e}")
        logger.error("请确保 utils/chrome_cleanup.py 文件存在")
        return {"success": False, "error": "import_error"}
        
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
        return {"success": False, "error": str(e)}

def test_file_utils_integration():
    """测试file_utils集成"""
    logger.info("=== 测试file_utils集成 ===")
    
    try:
        from utils.file_utils import kill_chrome_processes
        
        logger.info("测试kill_chrome_processes函数...")
        result = kill_chrome_processes()
        logger.info(f"kill_chrome_processes结果: {result}")
        
        return {"success": True, "result": result}
        
    except Exception as e:
        logger.error(f"file_utils集成测试失败: {e}")
        return {"success": False, "error": str(e)}

def main():
    """主测试函数"""
    logger.info("Chrome清理工具测试开始")
    
    # 测试1: Chrome清理工具
    cleanup_result = test_chrome_cleanup()
    
    # 测试2: file_utils集成
    integration_result = test_file_utils_integration()
    
    # 输出测试总结
    logger.info("=== 测试总结 ===")
    logger.info(f"Chrome清理工具测试: {'通过' if cleanup_result.get('success') else '失败'}")
    logger.info(f"file_utils集成测试: {'通过' if integration_result.get('success') else '失败'}")
    
    if cleanup_result.get('success'):
        logger.info(f"清理效果: {cleanup_result.get('cleaned_count', 0)} / {cleanup_result.get('total_files', 0)} 文件被清理")
    
    # 返回整体测试结果
    overall_success = cleanup_result.get('success', False) and integration_result.get('success', False)
    
    if overall_success:
        logger.info("✅ 所有测试通过！Chrome清理工具工作正常")
    else:
        logger.error("❌ 部分测试失败，请检查错误信息")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
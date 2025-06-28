#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chrome清理工具 - 专门处理Chrome缓存和锁文件清理
"""

import os
import platform
import time
import logging
import glob
import shutil
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

class ChromeCleanup:
    """Chrome清理工具类"""
    
    def __init__(self):
        self.system = platform.system()
        
    def cleanup_all(self):
        """执行完整的Chrome清理"""
        logger.info("开始Chrome完整清理...")
        
        # 1. 清理用户数据目录
        self.cleanup_user_data_directories()
        
        # 2. 清理临时文件
        self.cleanup_temp_files()
        
        # 3. 清理系统临时Chrome文件
        self.cleanup_system_temp()
        
        logger.info("Chrome清理完成")
    
    def cleanup_user_data_directories(self):
        """清理Chrome用户数据目录（只清理锁文件，保留登录状态）"""
        directories = [
            "./chrome_user_data",
            os.path.expanduser("~/chrome_user_data"),
            "/app/chrome_user_data"
        ]
        
        for directory in directories:
            if os.path.exists(directory):
                logger.info(f"清理用户数据目录的锁文件: {directory}")
                self.cleanup_chrome_directory(directory)
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        temp_directories = [
            "/tmp/chrome_tmp",
            os.path.join(os.environ.get('TEMP', '/tmp'), "chrome_tmp"),
            os.path.join(os.environ.get('TMPDIR', '/tmp'), "chrome_tmp")
        ]
        
        for directory in temp_directories:
            if os.path.exists(directory):
                # 临时目录可以完全清理
                logger.info(f"清理临时Chrome目录: {directory}")
                try:
                    shutil.rmtree(directory)
                    logger.debug(f"已删除临时目录: {directory}")
                except Exception as e:
                    logger.debug(f"删除临时目录失败: {directory} - {e}")
    
    def cleanup_system_temp(self):
        """清理系统临时Chrome文件"""
        if self.system == "Windows":
            temp_dirs = [
                os.environ.get('TEMP', ''),
                os.environ.get('TMP', ''),
                r"C:\Windows\Temp"
            ]
        else:
            temp_dirs = [
                "/tmp",
                "/var/tmp",
                os.environ.get('TMPDIR', '/tmp')
            ]
        
        for temp_dir in temp_dirs:
            if not temp_dir or not os.path.exists(temp_dir):
                continue
                
            try:
                # 查找Chrome相关临时文件
                chrome_patterns = [
                    os.path.join(temp_dir, "chrome_*"),
                    os.path.join(temp_dir, "scoped_dir*"),
                    os.path.join(temp_dir, ".org.chromium.Chromium.*")
                ]
                
                for pattern in chrome_patterns:
                    for item in glob.glob(pattern):
                        self.safe_remove(item, is_temp=True)
                        
            except Exception as e:
                logger.debug(f"清理系统临时目录 {temp_dir} 时出错: {e}")
    
    def cleanup_chrome_directory(self, directory):
        """清理指定的Chrome目录"""
        if not os.path.exists(directory):
            return
            
        logger.info(f"清理Chrome目录: {directory}")
        
        # 只清理锁文件和临时文件，保留登录状态
        lock_files = [
            "SingletonLock",
            "SingletonCookie", 
            "SingletonSocket"
        ]
        
        # 临时文件模式（可以安全删除）
        temp_patterns = [
            "Default/*-journal",  # 数据库日志文件
            "Default/*.tmp",      # 临时文件
            "Default/GPUCache/*", # GPU缓存
            "Default/Code Cache/*", # 代码缓存
        ]
        
        # 缓存文件模式（删除失败也没关系）
        cache_patterns = [
            "Default/Cache/Cache_Data/index*",
            "Default/Cache/Cache_Data/data_*",
        ]
        
        # 需要保留的登录状态文件（不删除）
        preserve_patterns = [
            "Default/Cookies",           # 登录cookies
            "Default/Preferences",       # 用户首选项
            "Default/Local State",       # 本地状态
            "Default/Web Data",          # 登录相关数据
            "Default/Login Data",        # 登录数据
            "Default/Network Persistent State", # 网络状态
            "Default/TransportSecurity", # 传输安全状态
        ]
        
        # 清理锁文件
        for item in lock_files:
            item_path = os.path.join(directory, item)
            if self.safe_remove(item_path):
                logger.debug(f"清理锁文件: {item}")
        
        # 清理临时文件
        for pattern in temp_patterns:
            full_pattern = os.path.join(directory, pattern)
            try:
                for temp_file in glob.glob(full_pattern):
                    # 确保不误删保留文件
                    should_preserve = False
                    for preserve_pattern in preserve_patterns:
                        preserve_path = os.path.join(directory, preserve_pattern)
                        if os.path.samefile(temp_file, preserve_path) if os.path.exists(preserve_path) else False:
                            should_preserve = True
                            break
                    
                    if not should_preserve:
                        self.safe_remove(temp_file)
                        logger.debug(f"清理临时文件: {os.path.relpath(temp_file, directory)}")
            except Exception as e:
                logger.debug(f"清理临时文件模式 {pattern} 时出错: {e}")
        
        # 清理缓存文件（允许失败，不记录为错误）
        for pattern in cache_patterns:
            full_pattern = os.path.join(directory, pattern)
            try:
                for cache_file in glob.glob(full_pattern):
                    if self.safe_remove(cache_file, is_cache=True):
                        logger.debug(f"清理缓存文件: {os.path.relpath(cache_file, directory)}")
            except Exception as e:
                logger.debug(f"清理缓存模式 {pattern} 时出错: {e}")
        
        logger.debug(f"Chrome目录清理完成，已保留登录状态文件")
    
    def safe_remove(self, path, is_cache=False, is_temp=False):
        """安全删除文件或目录"""
        if not os.path.exists(path):
            return True
            
        max_retries = 3 if not is_cache else 1
        
        for attempt in range(max_retries):
            try:
                # 尝试修改权限
                self.fix_permissions(path)
                
                if os.path.isfile(path):
                    os.remove(path)
                    if not is_cache and not is_temp:
                        logger.debug(f"已删除文件: {path}")
                elif os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                    if not is_cache and not is_temp:
                        logger.debug(f"已删除目录: {path}")
                
                return True
                
            except PermissionError as e:
                if is_cache:
                    # 缓存文件删除失败是正常现象
                    logger.debug(f"缓存文件正在使用，跳过: {os.path.basename(path)}")
                    return False
                    
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                else:
                    logger.debug(f"权限不足，无法删除: {path}")
                    return False
                    
            except FileNotFoundError:
                return True
                
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.2)
                    continue
                else:
                    if not is_cache:
                        logger.debug(f"删除失败: {path} - {e}")
                    return False
        
        return False
    
    def fix_permissions(self, path):
        """修复文件权限"""
        try:
            if os.path.isfile(path):
                # 文件权限
                os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            elif os.path.isdir(path):
                # 目录权限
                os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                # 递归修复目录内文件权限
                for root, dirs, files in os.walk(path):
                    for file in files:
                        try:
                            file_path = os.path.join(root, file)
                            os.chmod(file_path, stat.S_IWRITE | stat.S_IREAD)
                        except:
                            pass
        except:
            pass
    
    def is_chrome_running(self):
        """检查Chrome是否仍在运行"""
        try:
            if self.system == "Windows":
                result = os.system("tasklist /FI \"IMAGENAME eq chrome.exe\" 2>NUL | find /I \"chrome.exe\" >NUL")
                return result == 0
            else:
                result = os.system("pgrep -f chrome > /dev/null 2>&1")
                return result == 0
        except:
            return False
    
    def wait_for_chrome_exit(self, timeout=10):
        """等待Chrome进程完全退出"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_chrome_running():
                return True
            time.sleep(0.5)
        return False

def cleanup_chrome_files():
    """便捷函数：执行Chrome文件清理"""
    cleaner = ChromeCleanup()
    
    # 等待Chrome退出
    if cleaner.is_chrome_running():
        logger.info("等待Chrome进程退出...")
        cleaner.wait_for_chrome_exit()
    
    # 执行清理
    cleaner.cleanup_all()

if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 执行清理
    cleanup_chrome_files()
    print("Chrome清理完成") 
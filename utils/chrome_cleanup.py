#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chrome清理工具 - 专门处理Chrome缓存和锁文件清理
"""

import os
import psutil
import time
import logging
import shutil
import glob
from pathlib import Path

logger = logging.getLogger(__name__)

class BrowserCleanup:
    """浏览器清理工具，支持Chrome和Edge浏览器"""
    
    def __init__(self, browser_type="chrome"):
        """
        初始化浏览器清理工具
        
        Args:
            browser_type: 浏览器类型，可选值为"chrome"或"edge"
        """
        self.browser_type = browser_type.lower()
        if self.browser_type == "chrome":
            self.process_names = ["chrome", "chromedriver", "Google Chrome"]
            self.user_data_dir = os.environ.get("CHROME_USER_DATA_DIR", "chrome_user_data")
        elif self.browser_type == "edge":
            self.process_names = ["msedge", "msedgedriver", "Microsoft Edge"]
            self.user_data_dir = os.environ.get("EDGE_USER_DATA_DIR", "edge_user_data")
        else:
            raise ValueError(f"不支持的浏览器类型: {browser_type}")
    
    def is_browser_running(self):
        """检查浏览器进程是否在运行"""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                process_name = proc.info['name'].lower()
                for name in self.process_names:
                    if name.lower() in process_name:
                        logger.info(f"检测到{self.browser_type}进程: {process_name} (PID: {proc.info['pid']})")
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False
    
    def kill_browser_processes(self):
        """终止所有浏览器相关进程"""
        killed = False
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                process_name = proc.info['name'].lower()
                for name in self.process_names:
                    if name.lower() in process_name:
                        logger.info(f"终止{self.browser_type}进程: {process_name} (PID: {proc.info['pid']})")
                        proc.kill()
                        killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        return killed
    
    def wait_for_browser_exit(self, timeout=5):
        """等待浏览器进程退出
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            bool: 是否成功等待所有进程退出
        """
        start_time = time.time()
        while self.is_browser_running():
            if time.time() - start_time > timeout:
                logger.warning(f"{self.browser_type}进程在{timeout}秒内未完全退出")
                return False
            logger.info(f"等待{self.browser_type}进程退出...")
            time.sleep(0.5)
        
        logger.info(f"所有{self.browser_type}进程已退出")
        return True
    
    def clean_user_data(self):
        """清理浏览器用户数据目录"""
        if not self.user_data_dir:
            logger.warning(f"未设置{self.browser_type}用户数据目录")
            return False
        
        try:
            if os.path.exists(self.user_data_dir):
                logger.info(f"清理{self.browser_type}用户数据目录: {self.user_data_dir}")
                shutil.rmtree(self.user_data_dir, ignore_errors=True)
                os.makedirs(self.user_data_dir, exist_ok=True)
                return True
            else:
                logger.info(f"{self.browser_type}用户数据目录不存在: {self.user_data_dir}")
                return False
        except Exception as e:
            logger.error(f"清理{self.browser_type}用户数据时出错: {e}")
            return False
    
    def clean_temp_files(self):
        """清理浏览器临时文件"""
        patterns = []
        if self.browser_type == "chrome":
            patterns = [
                "/tmp/chrome_*",
                "/tmp/.com.google.Chrome.*",
                "/tmp/.org.chromium.Chromium.*",
                "/var/tmp/chrome_*"
            ]
        elif self.browser_type == "edge":
            patterns = [
                "/tmp/edge_*",
                "/tmp/.com.microsoft.Edge.*",
                "/var/tmp/edge_*"
            ]
        
        try:
            for pattern in patterns:
                for path in glob.glob(pattern):
                    if os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                    else:
                        os.remove(path)
            logger.info(f"已清理{self.browser_type}临时文件")
            return True
        except Exception as e:
            logger.error(f"清理{self.browser_type}临时文件时出错: {e}")
            return False
    
    def full_cleanup(self):
        """执行完整清理"""
        # 先终止进程
        self.kill_browser_processes()
        
        # 等待进程退出
        self.wait_for_browser_exit()
        
        # 清理用户数据
        self.clean_user_data()
        
        # 清理临时文件
        self.clean_temp_files()
        
        logger.info(f"{self.browser_type}浏览器环境已完全清理")
        return True


# 为了向后兼容，保留ChromeCleanup类
class ChromeCleanup(BrowserCleanup):
    def __init__(self):
        super().__init__(browser_type="chrome")
        
    def is_chrome_running(self):
        """检查浏览器进程是否在运行（兼容旧接口）"""
        return self.is_browser_running()


# 新增EdgeCleanup类
class EdgeCleanup(BrowserCleanup):
    def __init__(self):
        super().__init__(browser_type="edge")
        
    def wait_for_chrome_exit(self, timeout=5):
        """兼容旧接口，等待浏览器进程退出"""
        return self.wait_for_browser_exit(timeout)
        
    def is_chrome_running(self):
        """兼容旧接口，检查浏览器进程是否在运行"""
        return self.is_browser_running() 
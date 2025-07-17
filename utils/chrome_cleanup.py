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
from typing import List, Optional

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


class ChromeCleanup:
    """Chrome浏览器清理工具类"""
    
    @staticmethod
    def clean_chrome_temp_files(chrome_user_data_dir: str) -> None:
        """清理Chrome浏览器的临时文件
        
        Args:
            chrome_user_data_dir: Chrome用户数据目录路径
        """
        if not os.path.exists(chrome_user_data_dir):
            logger.warning(f"Chrome用户数据目录不存在: {chrome_user_data_dir}")
            return
        
        # 需要清理的目录和文件模式
        patterns_to_clean = [
            os.path.join(chrome_user_data_dir, "*", "Cache", "*"),
            os.path.join(chrome_user_data_dir, "*", "Code Cache", "*"),
            os.path.join(chrome_user_data_dir, "*", "GPUCache", "*"),
            os.path.join(chrome_user_data_dir, "*", "Service Worker", "CacheStorage", "*"),
            os.path.join(chrome_user_data_dir, "*", "Service Worker", "ScriptCache", "*"),
            os.path.join(chrome_user_data_dir, "*", "Application Cache", "*"),
            os.path.join(chrome_user_data_dir, "*", "JumpListIconsRecentClosed", "*"),
            os.path.join(chrome_user_data_dir, "*", "JumpListIconsTopSites", "*"),
            os.path.join(chrome_user_data_dir, "*", "Network", "Cookies"),
            os.path.join(chrome_user_data_dir, "*", "Network", "Cookies-journal"),
            os.path.join(chrome_user_data_dir, "*", "*.tmp"),
            os.path.join(chrome_user_data_dir, "*", "*.log"),
        ]
        
        # 遍历并清理文件
        for pattern in patterns_to_clean:
            try:
                files = glob.glob(pattern)
                for file_path in files:
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path, ignore_errors=True)
                    except Exception as e:
                        logger.debug(f"清理文件失败: {file_path}, 错误: {e}")
            except Exception as e:
                logger.debug(f"处理模式 {pattern} 时出错: {e}")
        
        logger.info(f"Chrome临时文件清理完成: {chrome_user_data_dir}")


def clean_browser_user_data(base_dir: Optional[str] = None) -> None:
    """清理浏览器的用户数据目录，特别是临时任务目录
    
    Args:
        base_dir: 浏览器用户数据的基础目录，如果为None则使用默认目录
    """
    if base_dir is None:
        # 使用默认目录
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "edge_user_data")
    
    if not os.path.exists(base_dir):
        logger.warning(f"浏览器用户数据目录不存在: {base_dir}")
        return
    
    logger.info(f"开始清理浏览器用户数据目录: {base_dir}")
    
    # 清理临时任务目录
    task_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and d.startswith("task_")]
    
    if task_dirs:
        logger.info(f"发现 {len(task_dirs)} 个临时任务目录，开始清理...")
        for task_dir in task_dirs:
            try:
                full_path = os.path.join(base_dir, task_dir)
                logger.debug(f"正在删除临时目录: {full_path}")
                shutil.rmtree(full_path, ignore_errors=True)
            except Exception as e:
                logger.warning(f"删除临时目录 {task_dir} 失败: {e}")
    else:
        logger.info("没有发现临时任务目录")
    
    # 清理主用户数据目录中的缓存文件
    try:
        ChromeCleanup.clean_chrome_temp_files(base_dir)
    except Exception as e:
        logger.warning(f"清理主用户数据目录缓存失败: {e}")
    
    logger.info("浏览器用户数据目录清理完成")


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 执行清理
    clean_browser_user_data()
    print("浏览器用户数据清理完成") 
import os
import platform
import subprocess
import time
import json
import pickle
import requests
from typing import Dict, Any, Optional, Union
import mimetypes
import uuid
from datetime import datetime
import logging
import glob
import shutil
import stat

logger = logging.getLogger(__name__)

def safe_remove_file(file_path):
    """安全删除文件，包含重试和权限处理"""
    if not os.path.exists(file_path):
        return True
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 尝试修改权限后删除
            if os.path.isfile(file_path):
                # 修改文件权限
                try:
                    os.chmod(file_path, stat.S_IWRITE | stat.S_IREAD)
                except:
                    pass
                os.remove(file_path)
            elif os.path.isdir(file_path):
                # 如果是目录，使用shutil.rmtree
                shutil.rmtree(file_path, ignore_errors=True)
            return True
        except PermissionError:
            # 权限错误，等待后重试
            time.sleep(0.5)
            continue
        except FileNotFoundError:
            # 文件已不存在
            return True
        except Exception as e:
            logger.debug(f"删除文件 {file_path} 时出错 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return False
            time.sleep(0.5)
    return False

def force_kill_processes(process_names):
    """强制终止指定名称的进程
    
    Args:
        process_names: 进程名称列表
    """
    try:
        system = platform.system()
        
        for process_name in process_names:
            if system == "Windows":
                # Windows使用taskkill强制终止
                subprocess.run(f"taskkill /f /im {process_name}.exe", shell=True, 
                             capture_output=True, text=True)
            else:
                # Unix系统使用pkill强制终止
                subprocess.run(f"pkill -9 -f '{process_name}'", shell=True, 
                             capture_output=True, text=True)
        
        time.sleep(1)  # 等待进程完全终止
        logger.debug(f"已强制终止进程: {process_names}")
        
    except Exception as e:
        logger.debug(f"强制终止进程时出错: {e}")

def kill_chrome_processes():
    """根据操作系统类型终止Chrome进程"""
    try:
        logger.info("开始清理Chrome进程...")
        
        # 使用新的Chrome清理工具，但只清理进程，不清理用户数据
        from utils.chrome_cleanup import ChromeCleanup
        cleaner = ChromeCleanup()
        
        # 第一阶段：温和的进程终止
        system = platform.system()
        if system == "Windows":
            subprocess.run("taskkill /im chrome.exe /t", shell=True, 
                         capture_output=True, text=True)
            subprocess.run("taskkill /im chromedriver.exe /t", shell=True, 
                         capture_output=True, text=True)
        elif system == "Darwin":
            subprocess.run("pkill -f 'Google Chrome'", shell=True, 
                         capture_output=True, text=True)
            subprocess.run("pkill -f 'chromedriver'", shell=True, 
                         capture_output=True, text=True)
        else:
            # Linux系统
            subprocess.run("pkill -f chrome", shell=True, 
                         capture_output=True, text=True)
            subprocess.run("pkill -f chromedriver", shell=True, 
                         capture_output=True, text=True)
        
        # 等待进程自然终止
        time.sleep(2)
        
        # 第二阶段：强制终止仍在运行的进程
        force_kill_processes(['chrome', 'chromedriver', 'Google Chrome'])
        
        # 等待Chrome完全退出
        cleaner.wait_for_chrome_exit(timeout=5)
        
        # 第三阶段：只清理锁文件，保留登录状态
        try:
            # 只清理用户数据目录的锁文件，不删除登录状态
            cleaner.cleanup_user_data_directories()
            # 完全清理临时目录
            cleaner.cleanup_temp_files()
        except Exception as e:
            logger.debug(f"Chrome文件清理时出现非关键错误: {e}")
        
        logger.info("Chrome进程清理完成，已保留登录状态")
        return True
        
    except Exception as e:
        logger.error(f"Chrome进程清理失败: {e}")
        return False



def save_cookies(driver, filename):
    """保存浏览器cookies到文件
    
    Args:
        driver: WebDriver实例
        filename: 保存cookies的文件路径
        
    Returns:
        bool: 保存成功返回True，否则返回False
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        # 获取所有cookies
        cookies = driver.get_cookies()
        
        # 根据文件扩展名选择保存格式
        if filename.endswith('.json'):
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(cookies, f)
        else:
            with open(filename, 'wb') as f:
                pickle.dump(cookies, f)
                
        logger.info(f"Cookies已保存到: {filename}")
        return True
    except Exception as e:
        logger.error(f"保存cookies时出错: {e}")
        return False

def load_cookies(driver, filename):
    """从文件加载cookies到浏览器
    
    Args:
        driver: WebDriver实例
        filename: cookies文件路径
        
    Returns:
        bool: 加载成功返回True，否则返回False
    """
    if not os.path.exists(filename):
        logger.warning(f"Cookies文件不存在: {filename}")
        return False
        
    try:
        # 根据文件扩展名选择加载格式
        if filename.endswith('.json'):
            with open(filename, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
        else:
            with open(filename, 'rb') as f:
                cookies = pickle.load(f)
        
        # 添加cookies到浏览器
        for cookie in cookies:
            # 处理某些浏览器要求的特殊格式
            if 'expiry' in cookie:
                cookie['expiry'] = int(cookie['expiry'])
            
            try:
                driver.add_cookie(cookie)
            except Exception:
                # 某些cookie可能添加失败，继续添加其他cookie
                pass
                
        return True
    except Exception as e:
        logger.error(f"加载cookies时出错: {e}")
        return False

class FileUtils:
    """文件工具类，提供文件上传等功能"""
    
    UPLOAD_URL = "https://pichub.8008893.workers.dev/upload"
    TOKEN = "pic-EreLRazcAnLekI0ZieUBynQoJyAoMT8X"
    
    @classmethod
    def upload_file(cls, file_path: str) -> Dict[str, Any]:
        """
        上传文件到图片服务器
        
        Args:
            file_path: 文件的本地路径
            
        Returns:
            Dict: 包含上传结果的字典，格式如下:
            {
                "success": true,
                "filename": "xxx.jpg",
                "url": "https://pichub.8008893.workers.dev/images/xxx.jpg",
                "contentType": "image/jpeg",
                "uploadedAt": "2025-06-15T06:42:36.176Z",
                "originalName": "xxx.jpg",
                "fileSize": 123456,
                "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            }
        
        Raises:
            FileNotFoundError: 如果文件不存在
            Exception: 上传过程中的其他错误
        """
        # 导入配置
        from config.settings import settings
        
        # 标准化文件路径，处理可能的编码问题
        from utils.file_format_utils import normalize_filename
        file_path = normalize_filename(file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            # 如果标准化后的路径不存在，尝试在同目录查找匹配的文件
            file_dir = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            if os.path.exists(file_dir):
                # 尝试查找匹配的文件
                pattern = os.path.join(file_dir, "*" + os.path.splitext(file_name)[1])
                matching_files = glob.glob(pattern)
                if matching_files:
                    # 使用第一个匹配的文件
                    file_path = matching_files[0]
                    logger.info(f"使用找到的匹配文件: {file_path}")
                else:
                    raise FileNotFoundError(f"文件不存在: {file_path}")
            else:
                raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 根据UPLOAD_DRIVER配置选择处理方式
        if settings.UPLOAD_DRIVER == "local":
            # 本地模式：直接拼接完整URL
            filename = os.path.basename(file_path)
            
            # 确保文件名是UTF-8编码的
            try:
                filename = filename.encode('utf-8').decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                # 如果编码出错，使用原文件名
                pass
            
            # 构建本地文件URL
            # 移除APP_DOMAIN末尾的斜杠（如果有）
            domain = settings.APP_DOMAIN.rstrip('/')
            # 确保MEDIA_PREFIX以斜杠开头（如果没有）
            media_prefix = settings.MEDIA_PREFIX if settings.MEDIA_PREFIX.startswith('/') else f"/{settings.MEDIA_PREFIX}"
            # 移除MEDIA_PREFIX末尾的斜杠（如果有）
            media_prefix = media_prefix.rstrip('/')
            
            file_url = f"{domain}{media_prefix}/{filename}"
            
            # 返回本地模式的响应格式
            return {
                "success": True,
                "filename": filename,
                "url": file_url,
                "contentType": cls._get_content_type(file_path),
                "fileSize": os.path.getsize(file_path)
            }
        else:
            # r2模式：使用原有的上传逻辑
            return cls._upload_to_r2(file_path)
    
    @classmethod
    def _upload_to_r2(cls, file_path: str) -> Dict[str, Any]:
        """上传文件到R2存储"""
        # 准备请求头
        headers = {
            "Authorization": f"Bearer {cls.TOKEN}"
        }
        
        # 获取文件MIME类型
        mime_type = cls._get_content_type(file_path)
        
        # 准备文件表单数据
        filename = os.path.basename(file_path)
        files = {
            "file": (filename, open(file_path, "rb"), mime_type)
        }
        
        try:
            # 发送请求
            response = requests.post(
                cls.UPLOAD_URL, 
                headers=headers, 
                files=files
            )
            
            # 关闭文件
            files["file"][1].close()
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析并返回响应
            return response.json()
        
        except requests.RequestException as e:
            raise Exception(f"上传文件失败: {str(e)}")
    
    @classmethod
    def _get_content_type(cls, file_path: str) -> str:
        """获取文件的MIME类型"""
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            # 如果无法确定MIME类型，根据扩展名设置默认值
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.xlsx':
                mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            elif ext == '.pdf':
                mime_type = 'application/pdf'
            elif ext == '.png':
                mime_type = 'image/png'
            elif ext == '.jpg' or ext == '.jpeg':
                mime_type = 'image/jpeg'
            else:
                mime_type = 'application/octet-stream'
        return mime_type

    @classmethod
    def get_file_url(cls, file_path: str) -> Optional[str]:
        """
        上传文件并返回文件URL
        
        Args:
            file_path: 文件的本地路径
            
        Returns:
            str: 上传成功后的文件URL
            None: 上传失败
        """
        try:
            result = cls.upload_file(file_path)
            if result.get("success"):
                return result.get("url")
            return None
        except Exception:
            return None

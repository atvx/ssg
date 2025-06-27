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

logger = logging.getLogger(__name__)

def kill_chrome_processes():
    """根据操作系统类型终止Chrome进程"""
    system = platform.system()
    
    try:
        if system == "Windows":
            # Windows系统
            os.system("taskkill /f /im chrome.exe >nul 2>&1")
            os.system("taskkill /f /im chromedriver.exe >nul 2>&1")
        elif system == "Darwin":
            # macOS系统
            subprocess.run("pkill -f 'Google Chrome'", shell=True)
            subprocess.run("pkill -f 'chromedriver'", shell=True)
        else:
            # Linux及其他系统 - 使用更全面的方法
            print("在Linux环境中清理Chrome进程...")
            
            # 使用多种方法检测和清理Chrome相关进程
            try:
                # 使用ps命令查找Chrome相关进程
                try:
                    ps_cmd = "ps -ef | grep -i 'chrom' | grep -v grep"
                    print(f"执行命令: {ps_cmd}")
                    ps_output = subprocess.check_output(ps_cmd, shell=True, text=True)
                    print(f"找到以下Chrome相关进程:\n{ps_output}")
                except subprocess.CalledProcessError:
                    print("未找到Chrome相关进程")
                
                # 1. 先使用pkill尝试正常终止进程
                print("使用pkill终止进程...")
                subprocess.run("pkill -f chrome", shell=True)
                subprocess.run("pkill -f chromedriver", shell=True)
                
                # 2. 等待短暂时间
                time.sleep(1)
                
                # 3. 强制终止顽固进程
                print("强制终止顽固进程...")
                subprocess.run("pkill -9 -f chrome", shell=True)
                subprocess.run("pkill -9 -f chromedriver", shell=True)
                
                # 4. 使用killall命令作为备选方案
                print("使用killall命令...")
                # 不使用capture_output，改为重定向stderr
                subprocess.run("killall -9 chrome 2>/dev/null || true", shell=True)
                subprocess.run("killall -9 chromedriver 2>/dev/null || true", shell=True)
                
                # 5. 清理进程组
                print("清理进程组...")
                subprocess.run("pkill -9 -g chrome 2>/dev/null || true", shell=True)
                
                # 6. 逐个处理进程 - 获取所有PID并直接杀死
                try:
                    # 直接获取PID列表
                    pid_cmd = "ps -eo pid,comm | grep -i chrom | grep -v grep | awk '{print $1}'"
                    pid_list = subprocess.check_output(pid_cmd, shell=True, text=True).strip().split('\n')
                    
                    for pid in pid_list:
                        if pid.strip():
                            try:
                                # 直接使用kill -9 杀死进程
                                subprocess.run(f"kill -9 {pid}", shell=True)
                            except:
                                pass
                except:
                    pass
                
                # 7. 清理僵尸进程的父进程
                try:
                    ppid_cmd = "ps -eo ppid,stat | grep -i Z | grep -v grep | awk '{print $1}' | sort | uniq"
                    ppid_list = subprocess.check_output(ppid_cmd, shell=True, text=True).strip().split('\n')
                    
                    for ppid in ppid_list:
                        if ppid.strip() and ppid.strip() != "1":  # 不杀PID为1的进程
                            try:
                                subprocess.run(f"kill -9 {ppid}", shell=True)
                            except:
                                pass
                except:
                    pass
                    
            except Exception as e:
                print(f"Chrome进程清理过程中出错: {e}")
            
        # 等待进程终止
        time.sleep(2)
        
        # 清理用户数据目录中的锁文件
        try:
            print("清理Chrome用户数据目录锁文件...")
            
            # 根据不同操作系统使用不同的清理方法
            if system == "Windows":
                # Windows系统使用通配符删除
                lock_patterns = [
                    r".\chrome_user_data\Default\*lock*",
                    r".\chrome_user_data\*SingletonLock*",
                    r".\chrome_user_data\*SingletonCookie*",
                    r".\chrome_user_data\*SingletonSocket*",
                    r".\chrome_user_data\Default\Cache\Cache_Data\index*",
                    r".\chrome_user_data\Default\Cache\Cache_Data\data*",
                    r".\tmp\chrome_tmp\*lock*",
                    r".\tmp\chrome_tmp\*Singleton*"
                ]
                
                for pattern in lock_patterns:
                    try:
                        os.system(f"del /F /Q {pattern} 2>nul")
                    except:
                        pass
                        
            else:
                # Linux/Mac系统
                lock_files = [
                    "./chrome_user_data/SingletonLock",
                    "./chrome_user_data/SingletonCookie",
                    "./chrome_user_data/SingletonSocket",
                    "./chrome_user_data/.org.chromium.Chromium.*/SingletonLock",
                    "./chrome_user_data/Default/Cache/Cache_Data/index*",
                    "./chrome_user_data/Default/Cache/Cache_Data/data*",
                    "/tmp/chrome_tmp/SingletonLock",
                    "/tmp/chrome_tmp/SingletonCookie",
                    "/tmp/chrome_tmp/SingletonSocket",
                    "/tmp/chrome_tmp/.org.chromium.Chromium.*/SingletonLock",
                    "/tmp/chrome_tmp/Default/Cache/Cache_Data/index*",
                    "/tmp/chrome_tmp/Default/Cache/Cache_Data/data*"
                ]
                
                for pattern in lock_files:
                    # 使用Python内置方法而不是shell命令
                    try:
                        import glob
                        for file_path in glob.glob(pattern):
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                print(f"已删除: {file_path}")
                    except Exception as e:
                        print(f"删除文件 {pattern} 时出错: {e}")
                
        except Exception as e:
            print(f"清理锁文件时出错: {e}")
            
        return True
    except Exception as e:
        print(f"终止Chrome进程失败: {e}")
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
                
        print(f"Cookies已保存到: {filename}")
        return True
    except Exception as e:
        print(f"保存cookies时出错: {e}")
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
        print(f"Cookies文件不存在: {filename}")
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
        print(f"加载cookies时出错: {e}")
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
                import glob
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

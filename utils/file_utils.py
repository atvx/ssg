import os
import platform
import subprocess
import time
import json
import pickle


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
            subprocess.run("pkill -f 'Google Chrome'", shell=True, capture_output=True)
            subprocess.run("pkill -f 'chromedriver'", shell=True, capture_output=True)
        else:
            # Linux及其他系统
            subprocess.run("pkill -f chrome", shell=True, capture_output=True)
            subprocess.run("pkill -f chromedriver", shell=True, capture_output=True)
            
        # 等待进程终止
        time.sleep(1)
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

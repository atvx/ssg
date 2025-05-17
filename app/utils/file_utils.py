import os
import platform
import subprocess
import time


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

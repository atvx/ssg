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
                subprocess.run("pkill -f chrome", shell=True, capture_output=True)
                subprocess.run("pkill -f chromedriver", shell=True, capture_output=True)
                
                # 2. 等待短暂时间
                time.sleep(1)
                
                # 3. 强制终止顽固进程
                print("强制终止顽固进程...")
                subprocess.run("pkill -9 -f chrome", shell=True, capture_output=True)
                subprocess.run("pkill -9 -f chromedriver", shell=True, capture_output=True)
                
                # 4. 使用killall命令作为备选方案
                print("使用killall命令...")
                subprocess.run("killall -9 chrome", shell=True, capture_output=True, stderr=subprocess.DEVNULL)
                subprocess.run("killall -9 chromedriver", shell=True, capture_output=True, stderr=subprocess.DEVNULL)
                
                # 5. 清理进程组
                print("清理进程组...")
                subprocess.run("pkill -9 -g chrome", shell=True, capture_output=True, stderr=subprocess.DEVNULL)
                
                # 6. 逐个处理进程
                try:
                    # 查找所有Chrome或Chromedriver相关进程
                    ps_output = subprocess.check_output("ps -ef | grep -i chrom | grep -v grep", shell=True, text=True)
                    lines = ps_output.strip().split('\n')
                    
                    if lines and lines[0]:
                        print(f"仍然存在 {len(lines)} 个Chrome相关进程，逐个终止...")
                        for line in lines:
                            if line.strip():
                                parts = line.split()
                                if len(parts) > 1:
                                    pid = parts[1]
                                    try:
                                        subprocess.run(f"kill -9 {pid}", shell=True, capture_output=True)
                                        print(f"已强制终止进程 PID: {pid}")
                                    except Exception as e:
                                        print(f"终止进程 {pid} 时出错: {e}")
                    else:
                        print("所有Chrome进程已成功终止")
                        
                except subprocess.CalledProcessError:
                    print("未找到剩余的Chrome进程")
                    
                # 7. 清理僵尸进程
                print("清理僵尸进程...")
                try:
                    zombie_cmd = "ps -ef | grep -i defunct | grep -v grep"
                    zombie_output = subprocess.check_output(zombie_cmd, shell=True, text=True)
                    if zombie_output.strip():
                        print(f"发现僵尸进程:\n{zombie_output}")
                        # 尝试终止父进程
                        for line in zombie_output.strip().split('\n'):
                            if line.strip():
                                parts = line.split()
                                if len(parts) > 2:
                                    ppid = parts[2]  # 父进程ID
                                    try:
                                        subprocess.run(f"kill -9 {ppid}", shell=True, capture_output=True)
                                        print(f"终止父进程 PPID: {ppid}")
                                    except:
                                        pass
                except subprocess.CalledProcessError:
                    print("未发现僵尸进程")
                    
            except Exception as e:
                print(f"Chrome进程清理过程中出错: {e}")
            
        # 等待进程终止
        time.sleep(2)
        
        # 清理用户数据目录中的锁文件
        try:
            print("清理Chrome用户数据目录锁文件...")
            lock_pattern = os.path.join(os.path.abspath("."), "**", "*.lock")
            singleton_pattern = os.path.join(os.path.abspath("."), "**", "SingletonLock")
            
            import glob
            # 查找所有锁文件
            lock_files = glob.glob(lock_pattern, recursive=True)
            singleton_files = glob.glob(singleton_pattern, recursive=True)
            
            # 删除锁文件
            for lock_file in lock_files + singleton_files:
                try:
                    print(f"删除锁文件: {lock_file}")
                    os.remove(lock_file)
                except Exception as e:
                    print(f"删除锁文件 {lock_file} 时出错: {e}")
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

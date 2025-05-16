import os
import time
import pickle
import platform
import subprocess


def save_cookies(driver, cookies_file):
    """保存cookies到文件"""
    try:
        if not driver:
            print("无法保存cookies: driver对象为空")
            return False
            
        cookies = driver.get_cookies()
        if not cookies:
            print("没有可保存的cookies")
            return False
            
        # 确保目录存在
        cookies_dir = os.path.dirname(cookies_file)
        if not os.path.exists(cookies_dir):
            os.makedirs(cookies_dir, exist_ok=True)
            print(f"创建目录: {cookies_dir}")
            
        # 保存cookie文件
        with open(cookies_file, 'wb') as file:
            pickle.dump(cookies, file)
        print(f"Cookies已保存到 {cookies_file}")
        
        # 保存本地存储
        try:
            local_storage = driver.execute_script("return Object.entries(localStorage);")
            if local_storage:
                local_storage_file = cookies_file.replace('.pkl', '_localStorage.pkl')
                with open(local_storage_file, 'wb') as file:
                    pickle.dump(local_storage, file)
        except Exception as e:
            print(f"保存localStorage时出错: {e}")
            
        return True
    except Exception as e:
        print(f"保存Cookies时出错: {e}")
        return False


def load_cookies(driver, cookies_file, verify=True):
    """从文件加载cookies
    
    Args:
        driver: WebDriver实例
        cookies_file: cookies文件路径
        verify: 是否验证cookies有效性
        
    Returns:
        bool: 是否成功加载有效cookies
    """
    try:
        if not os.path.exists(cookies_file):
            print(f"Cookie文件不存在: {cookies_file}")
            return False
            
        # 检查文件大小和修改时间
        file_size = os.path.getsize(cookies_file)
        if file_size < 10:  # 文件太小，可能是空的或损坏的
            print("Cookie文件为空或已损坏，将创建新的登录会话")
            return False
            
        # 检查文件修改时间
        last_modified = os.path.getmtime(cookies_file)
        current_time = time.time()
        file_age_days = (current_time - last_modified) / (24 * 3600)
        
        if file_age_days > 14:  # 如果文件超过14天没更新，可能已过期
            print(f"Cookie文件过期 ({file_age_days:.1f}天前创建)，将重新登录")
            return False
            
        try:
            with open(cookies_file, 'rb') as file:
                cookies = pickle.load(file)
            
            if not cookies or not isinstance(cookies, list) or len(cookies) == 0:
                print("Cookie文件格式无效或为空")
                return False
                
            # 添加cookies到driver
            for cookie in cookies:
                try:
                    if 'expiry' in cookie:
                        # 检查cookie是否过期
                        if isinstance(cookie['expiry'], (int, float)) and cookie['expiry'] < time.time():
                            print(f"跳过已过期的cookie: {cookie.get('name')}")
                            continue
                        # Selenium无法处理浮点数的expiry值
                        cookie['expiry'] = int(cookie['expiry'])
                    driver.add_cookie(cookie)
                except Exception as e:
                    print(f"添加cookie时出错 ({cookie.get('name')}): {e}")
            
            # 尝试加载localStorage
            try:
                local_storage_file = cookies_file.replace('.pkl', '_localStorage.pkl')
                if os.path.exists(local_storage_file):
                    with open(local_storage_file, 'rb') as file:
                        local_storage_items = pickle.load(file)
                        
                    if local_storage_items and isinstance(local_storage_items, list):
                        driver.execute_script("""
                        var items = arguments[0];
                        items.forEach(item => {
                            localStorage.setItem(item[0], item[1]);
                        });
                        """, local_storage_items)
            except Exception as e:
                print(f"加载localStorage时出错: {e}")
            
            print("成功加载之前保存的cookies")
            
            # 如果需要验证cookies有效性
            if verify:
                # 检查是否有常见的验证cookie
                auth_cookies = [c for c in cookies if c.get('name') in ['token', 'auth', 'sessionid', 'login_token']]
                if not auth_cookies:
                    print("未找到关键的身份验证cookie，可能需要重新登录")
                    return False
                    
                # 检查cookie过期时间
                now = time.time()
                expired_cookies = [c for c in auth_cookies if 'expiry' in c and c['expiry'] < now]
                if expired_cookies:
                    print("关键身份验证cookie已过期，需要重新登录")
                    return False
            
            return True
        except Exception as e:
            print(f"读取Cookie文件时出错: {e}")
            return False
    except Exception as e:
        print(f"加载Cookies过程中出错: {e}")
        return False


def kill_chrome_processes():
    """终止所有Chrome进程"""
    try:
        system = platform.system()
        if system == 'Windows':
            # Windows系统使用taskkill命令
            subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
            subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
        elif system == 'Linux':
            # Linux系统使用pkill命令
            subprocess.run(['pkill', '-f', 'chrome'], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'chromedriver'], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
        elif system == 'Darwin':
            # macOS系统
            subprocess.run(['pkill', '-f', 'Google Chrome'], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'chromedriver'], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
            
        print("已终止之前的Chrome进程")
        # 等待进程完全关闭
        time.sleep(1)
        return True
    except Exception:
        # 忽略任何错误
        return False 
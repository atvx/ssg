import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config.settings import ACCOUNT_CONFIG, SLIDER_VERIFY_MODE
from utils.browser_utils import handle_iframe_slider, handle_phone_verification
from utils.file_utils import save_cookies


def login_with_phone(driver, wait, phone_number):
    """使用手机号和验证码登录"""
    try:
        # 切换到登录iframe
        iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        driver.switch_to.frame(iframe)
        time.sleep(1)
    
        # 勾选协议复选框
        try:
            checkbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".ep-checkbox-container")))
            checkbox.click()
        except Exception:
            print("勾选协议复选框失败")
    
        # 输入手机号
        try:
            phone_field = wait.until(EC.presence_of_element_located((By.ID, "phone")))
            phone_field.clear()
            for char in phone_number:
                phone_field.send_keys(char)
                time.sleep(0.1)
        except Exception:
            try:
                phone_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='输入手机号']")))
                phone_field.clear()
                for char in phone_number:
                    phone_field.send_keys(char)
                    time.sleep(0.1)
            except:
                print("所有尝试输入手机号的方法都失败")
                return False
    
        # 点击获取验证码按钮
        verify_code_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".timer-button")))
        verify_code_btn.click()
        print("=" * 50)
        print("验证码已发送到手机，请注意查收")
        verify_code = input("请输入收到的验证码: ")
    
        # 输入验证码
        verify_code_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.ep-input.ep-sms-input")))
        verify_code_field.clear()
        for char in verify_code:
            verify_code_field.send_keys(char)
            time.sleep(0.1)
    
        # 点击登录按钮
        login_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "ep-login_btn")))
        login_button.click()
        
        # 处理可能出现的滑块验证
        time.sleep(1.5)
        handle_iframe_slider(driver, wait, SLIDER_VERIFY_MODE)
        
        # 检查是否需要手机验证码验证
        time.sleep(2)
        needs_phone_verification = driver.execute_script("""
        var verifyInput = document.getElementById('yodaVerification');
        var smsBtn = document.getElementById('yodaSmsCodeBtn');
        var title = document.getElementById('yodaTitle');
        
        return (verifyInput !== null && smsBtn !== null) || 
               (title !== null && title.textContent.includes('验证手机'));
        """)
        
        if needs_phone_verification:
            print("检测到需要手机验证码验证")
            handle_phone_verification(driver, wait)
        
        # 返回主框架
        driver.switch_to.default_content()
        time.sleep(3)
        
        # 检查登录状态
        login_success = False
        try:
            # 尝试通过URL判断是否登录成功
            current_url = driver.current_url
            if "selectorg" in current_url or "/web/rms-account/#/auth" not in current_url:
                login_success = True
            
            # 尝试查找登录后常见的元素
            if not login_success:
                success_elements = driver.find_elements(By.CSS_SELECTOR, ".org-profile, .user-profile, .username, .logout")
                if success_elements:
                    login_success = True
        except Exception as e:
            print(f"检查登录状态时出错: {e}")
            
        if login_success:
            print("登录成功")
            return True
        else:
            print("登录可能未成功，请检查页面状态")
            return False
    except Exception as e:
        print(f"手机号登录过程出现异常: {e}")
        return False


def login_with_account(driver, wait, cookies_file):
    """使用账号和密码登录"""
    # 切换到登录iframe
    try:
        # 等待页面加载
        time.sleep(2)
        
        # 查找登录iframe
        login_iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        
        # 切换到登录iframe
        driver.switch_to.frame(login_iframe)
        time.sleep(1)
    
        # 切换到账号登录tab
        account_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'ep-tab_item')][.//div[text()='账号登录']]")))
        account_tab.click()
        time.sleep(1)
    
        # 勾选协议复选框
        try:
            checkbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".ep-checkbox-container")))
            checkbox.click()
        except Exception:
            pass
        
        # 输入账号
        username_field = wait.until(EC.presence_of_element_located((By.ID, "login")))
        username_field.clear()
        for char in ACCOUNT_CONFIG["USERNAME"]:
            username_field.send_keys(char)
            time.sleep(0.1)
        
        # 输入密码
        password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
        password_field.clear()
        for char in ACCOUNT_CONFIG["PASSWORD"]:
            password_field.send_keys(char)
            time.sleep(0.1)
        
        # 点击登录按钮
        login_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "ep-login_btn")))
        login_button.click()
        
        # 处理滑块验证
        handle_iframe_slider(driver, wait, SLIDER_VERIFY_MODE)
        
        # 处理手机验证码验证
        time.sleep(2)
        needs_phone_verification = driver.execute_script("""
        var verifyInput = document.getElementById('yodaVerification');
        var smsBtn = document.getElementById('yodaSmsCodeBtn');
        var title = document.getElementById('yodaTitle');
        
        return (verifyInput !== null && smsBtn !== null) || 
               (title !== null && title.textContent.includes('验证手机'));
        """)
        
        if needs_phone_verification:
            print("检测到需要手机验证码验证")
            handle_phone_verification(driver, wait)
        
        # 返回主框架
        driver.switch_to.default_content()
        time.sleep(3)
        
        # 检查登录状态
        login_success = False
        try:
            # 尝试通过URL判断是否登录成功
            current_url = driver.current_url
            if "selectorg" in current_url or "/web/rms-account/#/auth" not in current_url:
                login_success = True
            
            # 尝试查找登录后常见的元素
            if not login_success:
                success_elements = driver.find_elements(By.CSS_SELECTOR, ".org-profile, .user-profile, .username, .logout")
                if success_elements:
                    login_success = True
                    
            # 检查本地存储和cookie中的令牌
            if not login_success:
                token_exists = driver.execute_script("""
                return document.cookie.indexOf('token') > -1 || 
                       document.cookie.indexOf('auth') > -1 ||
                       window.localStorage.getItem('token') !== null;
                """)
                if token_exists:
                    login_success = True
        except Exception:
            pass
        
        if login_success:
            print("登录成功")
            # 添加额外的等待，确保所有会话数据都已保存
            time.sleep(2)
            # 保存cookies
            save_cookies(driver, cookies_file)
            return True
        else:
            print("登录可能未成功，请检查页面状态")
            return False
    except Exception as e:
        print(f"登录过程出现异常: {e}")
        return False


def select_organization(driver, wait, target_org):
    """选择目标机构"""
    try:
        # 等待页面加载
        time.sleep(2)

        # 检查是否在选择机构页面
        if "selectorg" in driver.current_url:
            print(f"选择机构: {target_org}")
            
            # 使用JavaScript直接查找并点击目标机构
            js_code = f"""
            var found = false;
            var items = document.querySelectorAll('.org-item');
            for (var i = 0; i < items.length; i++) {{
                var nameDiv = items[i].querySelector('.name div:first-child');
                if (nameDiv && nameDiv.textContent.includes('{target_org}')) {{
                    var button = items[i].querySelector('button.saas-btn');
                    if (button) {{
                        button.click();
                        found = true;
                        break;
                    }}
                }}
            }}
            return found;
            """
            result = driver.execute_script(js_code)
            if result:
                time.sleep(2)
                return True
            else:
                print("未能找到目标机构")
                return False
        else:
            # 已经登录不需要选择机构
            print("不在机构选择页面，无法选择机构")
            return False
    except Exception as e:
        print(f"选择机构失败: {e}")
        return False 
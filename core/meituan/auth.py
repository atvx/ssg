import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import logging
import re
from datetime import datetime
from urllib.parse import urlparse
from utils.redis_utils import VerificationManager
from ws.manager import connection_manager

from config.settings import ACCOUNT_CONFIG, SLIDER_VERIFY_MODE
from utils.browser_utils import handle_iframe_slider
from utils.file_utils import save_cookies

logger = logging.getLogger(__name__)


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
        handle_iframe_slider(driver, wait)
        
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
            handle_phone_verification(driver)
        
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
        handle_iframe_slider(driver, wait)
        
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
            handle_phone_verification(driver)
        
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


def handle_phone_verification(driver, timeout=60):
    """
    处理手机号验证码验证
    """
    try:
        logger.info("开始处理手机验证码验证")
        # 等待验证码输入框出现
        wait = WebDriverWait(driver, 5)
        # 判断是否需要验证码
        try:
            # 查找验证码输入框
            sms_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='请输入验证码']")))
            logger.info("找到验证码输入框")
            
            # 点击发送验证码按钮
            try:
                # 尝试多种方式找到发送验证码按钮
                send_button = None
                try:
                    send_button = driver.find_element(By.ID, "yodaSmsCodeBtn")
                except Exception:
                    try:
                        send_button = driver.find_element(By.XPATH, "//span[contains(text(), '发送验证码')]/..")
                    except Exception:
                        try:
                            send_button = driver.find_element(By.CSS_SELECTOR, "button[class*='smsCodeBtn']")
                        except Exception:
                            # 最后尝试JavaScript查找
                            is_clicked = driver.execute_script("""
                            var btn = document.getElementById('yodaSmsCodeBtn');
                            if (!btn) {
                                btn = document.querySelector('button[class*="smsCodeBtn"]');
                            }
                            if (!btn) {
                                var allBtns = document.querySelectorAll('button');
                                for (var i = 0; i < allBtns.length; i++) {
                                    if (allBtns[i].textContent.includes('发送验证码')) {
                                        btn = allBtns[i];
                                        break;
                                    }
                                }
                            }
                            if (btn && !btn.disabled) {
                                btn.click();
                                return true;
                            }
                            return false;
                            """)
                            if is_clicked:
                                logger.info("使用JavaScript点击了发送验证码按钮")
            
                # 如果找到按钮，点击它
                if send_button and send_button.is_displayed() and send_button.is_enabled():
                    send_button.click()
                    logger.info("点击发送验证码按钮")
            except Exception as e:
                logger.error(f"点击发送验证码按钮失败: {e}")
            
            # 获取手机号
            phone_number = ""
            try:
                phone_elem = driver.find_element(By.XPATH, "//div[contains(@class, 'mobile')]")
                phone_number = phone_elem.text
            except Exception:
                try:
                    phone_elem = driver.find_element(By.XPATH, "//span[contains(text(), '发送验证码')]/../preceding-sibling::div")
                    phone_number = phone_elem.text
                except Exception:
                    # 最后尝试JavaScript获取
                    phone_number = driver.execute_script("""
                    var phoneElem = document.querySelector('.verify-phone');
                    if (phoneElem) {
                        return phoneElem.textContent.replace(/[^0-9]/g, '');
                    }
                    return '';
                    """)
            
            # 如果没有获取到手机号，使用备用值
            if not phone_number:
                phone_number = "未知手机号"
            else:
                # 清理手机号中的非数字字符
                phone_number = ''.join(filter(str.isdigit, phone_number))
                
            logger.info(f"获取到手机号: {phone_number}")
            
            # 创建验证任务
            task_id = VerificationManager.create_verification_task({
                "phone": phone_number,
                "message": f"请为手机 {phone_number} 输入美团验证码",
                "status": "pending"
            })
            
            # 使用同步方式发送WebSocket通知，避免coroutine not awaited错误
            try:
                # 创建通知消息
                message = {
                    "type": "verification_needed",
                    "task_id": task_id,
                    "message": f"请为手机 {phone_number} 输入美团验证码"
                }
                # 直接将消息记录到日志，而不是异步广播
                logger.warning(f"需要验证码: {message}")
                # 异步广播的替代方法
                import threading
                def broadcast_message():
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(connection_manager.broadcast(message))
                    loop.close()
                # 在后台线程中执行
                threading.Thread(target=broadcast_message).start()
            except Exception as e:
                logger.error(f"发送WebSocket通知失败: {e}")
            
            # 轮询等待验证码
            logger.info(f"等待验证码输入，任务ID: {task_id}")
            start_time = time.time()
            verification_code = None
            
            while time.time() - start_time < timeout:
                # 获取验证码状态
                task_info = VerificationManager.get_verification_task(task_id)
                
                if task_info and task_info.get("status") == "completed":
                    verification_code = VerificationManager.get_verification_code(task_id)
                    if verification_code:
                        logger.info(f"获取到验证码: {verification_code}")
                        break
                
                time.sleep(2)
            
            # 超时处理
            if not verification_code:
                logger.warning("验证码输入超时")
                VerificationManager.update_verification_status(task_id, {
                    "status": "timeout",
                    "message": "验证码输入超时"
                })
                # 使用同步方式发送超时通知
                try:
                    timeout_message = {
                        "type": "verification_timeout",
                        "task_id": task_id,
                        "message": "验证码输入超时"
                    }
                    logger.warning(f"验证码超时: {timeout_message}")
                except Exception as e:
                    logger.error(f"发送超时通知失败: {e}")
                return False
            
            # 输入验证码
            sms_input.clear()
            sms_input.send_keys(verification_code)
            logger.info("输入验证码完成")
            
            # 点击验证按钮
            try:
                submit_button = None
                try:
                    submit_button = driver.find_element(By.ID, "yodaSubmit")
                except Exception:
                    try:
                        submit_button = driver.find_element(By.XPATH, "//span[contains(text(), '验证')]/..")
                    except Exception:
                        try:
                            # 最后尝试JavaScript点击
                            is_clicked = driver.execute_script("""
                            var btn = document.getElementById('yodaSubmit');
                            if (!btn) {
                                btn = Array.from(document.querySelectorAll('button')).find(b => 
                                    b.textContent.includes('验证'));
                            }
                            if (btn) {
                                btn.disabled = false;
                                btn.click();
                                return true;
                            }
                            return false;
                            """)
                            if is_clicked:
                                logger.info("使用JavaScript点击了验证按钮")
                        except Exception:
                            pass
                
                if submit_button and submit_button.is_displayed():
                    submit_button.click()
                    logger.info("点击验证按钮")
            except Exception as e:
                logger.error(f"点击验证按钮失败: {e}")
            
            # 等待验证结果
            time.sleep(3)
            
            # 完成任务
            VerificationManager.update_verification_status(task_id, {
                "status": "success",
                "message": "验证码验证成功"
            })
            
            # 使用同步方式发送成功通知
            try:
                success_message = {
                    "type": "verification_success",
                    "task_id": task_id,
                    "message": "验证码验证成功"
                }
                logger.info(f"验证成功: {success_message}")
            except Exception as e:
                logger.error(f"发送成功通知失败: {e}")
            
            # 清理任务
            VerificationManager.remove_verification_task(task_id)
            logger.info("手机验证码验证完成")
            
            return True
        except (NoSuchElementException, TimeoutException) as e:
            logger.info(f"无需手机验证码: {e}")
            return True
    except Exception as e:
        logger.error(f"处理手机验证码验证失败: {e}")
        return False


def choose_organization(driver, wait, target_org):
    """
    选择目标组织
    
    Args:
        driver: WebDriver对象
        wait: WebDriverWait对象
        target_org: 目标组织名称
        
    Returns:
        bool: 成功返回True，失败返回False
    """
    logger.info(f"尝试选择组织: {target_org}")
    
    try:
        # 等待页面加载
        time.sleep(2)

        # 检查是否在选择机构页面
        if "selectorg" in driver.current_url:
            logger.info(f"在组织选择页面，将选择: {target_org}")
            
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
                logger.info("成功选择组织")
                time.sleep(2)
                return True
            else:
                logger.warning("未能找到目标组织")
                return False
        else:
            # 不在机构选择页面，可能已经选择好了
            logger.info("不在机构选择页面，可能已经选择好了组织")
            return True
    except Exception as e:
        logger.error(f"选择组织失败: {e}")
        return False


def check_login(driver):
    """
    检查是否已登录
    
    Args:
        driver: WebDriver对象
        
    Returns:
        bool: 已登录返回True，未登录返回False
    """
    try:
        # 等待页面加载
        time.sleep(2)
        
        # 检查URL是否包含登录相关信息
        current_url = driver.current_url
        if "login" in current_url.lower() or "/web/rms-account/#/auth" in current_url:
            # 可能未登录，检查是否有登录表单
            login_elements = driver.find_elements(By.CSS_SELECTOR, "input#login, input#password, .login-btn")
            if login_elements:
                logger.info("检测到登录表单，用户未登录")
                return False
                
        # 检查是否在选择机构页面
        if "selectorg" in current_url:
            logger.info("用户已登录，在选择机构页面")
            return True
            
        # 检查是否有登录后常见的元素
        logged_in_elements = driver.find_elements(By.CSS_SELECTOR, ".org-profile, .user-profile, .username, .logout")
        if logged_in_elements:
            logger.info("检测到已登录元素，用户已登录")
            return True
            
        # 检查cookies和localStorage中的登录信息
        token_exists = driver.execute_script("""
        return document.cookie.indexOf('token') > -1 || 
               document.cookie.indexOf('auth') > -1 ||
               window.localStorage.getItem('token') !== null;
        """)
        if token_exists:
            logger.info("检测到登录令牌，用户已登录")
            return True
            
        # 默认判断为未登录
        logger.info("未检测到登录状态，判断为未登录")
        return False
    except Exception as e:
        logger.error(f"检查登录状态出错: {e}")
        return False 
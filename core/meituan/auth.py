import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import logging
import re
from datetime import datetime
from urllib.parse import urlparse
from utils.redis_utils import VerificationManager, publish_ws_message
from ws.manager import connection_manager
from db.crud import get_ext_account_by_platform
from sqlalchemy.orm import Session

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


def login_with_account(driver, wait, cookies_file, db: Session = None, user_id: int = None, platform: str = "meituan"):
    """
    使用账号和密码登录
    
    Args:
        driver: WebDriver对象
        wait: WebDriverWait对象
        cookies_file: cookies文件路径
        db: 数据库会话（可选）
        user_id: 用户ID（可选）
        platform: 平台名称（默认为meituan）
    
    Returns:
        bool: 登录成功返回True，否则返回False
    """
    # 获取账号信息
    username = None
    password = None
    
    # 首先尝试从数据库获取账号信息
    if db and user_id:
        logger.info(f"尝试获取用户ID {user_id} 的 {platform} 平台账号信息")
        ext_account = get_ext_account_by_platform(db, user_id, platform)
        if ext_account:
            username = ext_account.username
            password = ext_account.password
            logger.info(f"从数据库获取到 {platform} 平台账号信息")
    
    # 如果数据库中没有账号信息，则使用配置文件中的账号信息
    if not username or not password:
        logger.warning(f"未从数据库获取到账号信息，将使用配置文件中的账号信息")
        username = ACCOUNT_CONFIG.get("USERNAME")
        password = ACCOUNT_CONFIG.get("PASSWORD")
        
    if not username or not password:
        logger.error("账号或密码未配置")
        return False
    
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
        for char in username:
            username_field.send_keys(char)
            time.sleep(0.1)
        
        # 输入密码
        password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
        password_field.clear()
        for char in password:
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
            logger.info("检测到需要手机验证码验证")
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
            logger.info("登录成功")
            # 添加额外的等待，确保所有会话数据都已保存
            time.sleep(2)
            # 保存cookies
            save_cookies(driver, cookies_file)
            return True
        else:
            logger.warning("登录可能未成功，请检查页面状态")
            return False
    except Exception as e:
        logger.error(f"登录过程出现异常: {e}")
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
                    
                    # 处理可能出现的滑块验证
                    time.sleep(1.5)  # 等待滑块加载
                    try:
                        from utils.browser_utils import handle_iframe_slider
                        
                        # 检查是否有iframe
                        iframes = driver.find_elements(By.TAG_NAME, "iframe")
                        
                        # 先检查主文档中是否有滑块
                        slider_elements = driver.find_elements(By.CSS_SELECTOR, ".yoda-slider-wrapper, .yodaBox-wrapper, #captcha-box, #yodaBox, .boxStatic")
                        
                        if slider_elements:
                            logger.info("发送验证码后在主文档中检测到滑块验证，尝试处理")
                            handle_iframe_slider(driver, WebDriverWait(driver, 10))
                            logger.info("滑块验证处理完成")
                        elif iframes:
                            logger.info(f"发现 {len(iframes)} 个iframe，尝试检查是否存在滑块验证")
                            # 保存当前上下文
                            current_context = driver.current_window_handle
                            
                            # 依次检查每个iframe
                            iframe_found = False
                            for i, iframe in enumerate(iframes):
                                try:
                                    driver.switch_to.frame(iframe)
                                    iframe_slider_elements = driver.find_elements(By.CSS_SELECTOR, ".yoda-slider-wrapper, .yodaBox-wrapper, #captcha-box, #yodaBox, .boxStatic")
                                    
                                    if iframe_slider_elements:
                                        logger.info(f"在iframe {i+1} 中发现滑块验证，尝试处理")
                                        handle_iframe_slider(driver, WebDriverWait(driver, 10))
                                        logger.info("滑块验证处理完成")
                                        iframe_found = True
                                        # 处理完滑块后，需要返回主文档
                                        driver.switch_to.default_content()
                                        break
                                    else:
                                        # 恢复到主文档
                                        driver.switch_to.default_content()
                                except Exception as e:
                                    logger.warning(f"检查iframe {i+1} 时出错: {e}")
                                    # 恢复到主文档
                                    driver.switch_to.default_content()
                            
                            # 无论是否找到滑块，确保最终回到主文档
                            try:
                                driver.switch_to.default_content()
                            except Exception:
                                pass
                            
                            # 如果没有在任何iframe中找到滑块，记录日志
                            if not iframe_found:
                                logger.info("在所有iframe中均未发现滑块验证")
                        else:
                            logger.info("发送验证码后未检测到滑块验证")
                    except Exception as e:
                        logger.warning(f"处理发送验证码后的滑块验证失败: {e}", exc_info=True)
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
            
            # 创建通知消息
            message = {
                "type": "verification_needed",
                "task_id": task_id,
                "message": f"请为手机 {phone_number} 输入美团验证码"
            }
            
            # 记录到日志
            logger.warning(f"需要验证码: {message}")
            
            # 通过Redis发布验证码通知，用于跨进程通信
            publish_result = publish_ws_message("verification", message)
            if publish_result:
                logger.info(f"验证码通知已通过Redis发布，任务ID: {task_id}")
            else:
                logger.error(f"验证码通知Redis发布失败，任务ID: {task_id}")
                
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
                
                # 发送超时通知
                timeout_message = {
                    "type": "verification_timeout",
                    "task_id": task_id,
                    "message": "验证码输入超时"
                }
                logger.warning(f"验证码超时: {timeout_message}")
                
                # 通过Redis发布超时通知
                publish_result = publish_ws_message("verification", timeout_message)
                if publish_result:
                    logger.info(f"超时通知已通过Redis发布，任务ID: {task_id}")
                else:
                    logger.error(f"超时通知Redis发布失败，任务ID: {task_id}")
                
                return False
            
            # 输入验证码
            try:
                # 确保验证码输入框仍然存在
                sms_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='请输入验证码']")))
                sms_input.clear()
                # 逐个字符输入，确保每个字符都能被正确输入
                for char in verification_code:
                    sms_input.send_keys(char)
                    time.sleep(0.1)
                logger.info(f"输入验证码完成: {verification_code}")
            except Exception as e:
                logger.error(f"输入验证码失败: {e}")
                return False
            
            # 点击验证按钮
            submit_success = False
            try:
                # 尝试多种方式找到并点击验证按钮
                # 1. 通过ID查找
                try:
                    submit_button = wait.until(EC.element_to_be_clickable((By.ID, "yodaSubmit")))
                    submit_button.click()
                    logger.info("通过ID找到并点击了验证按钮")
                    submit_success = True
                except Exception:
                    logger.info("通过ID查找验证按钮失败，尝试其他方法")
                
                # 2. 通过XPath查找
                if not submit_success:
                    try:
                        submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), '验证')]/parent::button")))
                        submit_button.click()
                        logger.info("通过XPath找到并点击了验证按钮")
                        submit_success = True
                    except Exception:
                        logger.info("通过XPath查找验证按钮失败，尝试其他方法")
                
                # 3. 最后尝试JavaScript点击
                if not submit_success:
                    try:
                        is_clicked = driver.execute_script("""
                        // 尝试多种选择器找到验证按钮
                        var btn = document.getElementById('yodaSubmit');
                        if (!btn) {
                            btn = document.querySelector('button[id*="submit" i], button[class*="submit" i]');
                        }
                        if (!btn) {
                            btn = Array.from(document.querySelectorAll('button')).find(b => 
                                b.textContent.includes('验证'));
                        }
                        if (btn) {
                            // 移除可能的禁用状态
                            btn.disabled = false;
                            btn.removeAttribute('disabled');
                            btn.click();
                            return true;
                        }
                        return false;
                        """)
                        if is_clicked:
                            logger.info("使用JavaScript找到并点击了验证按钮")
                            submit_success = True
                        else:
                            logger.warning("JavaScript无法找到验证按钮")
                    except Exception as js_error:
                        logger.error(f"JavaScript点击验证按钮时出错: {js_error}")
                
                # 检查是否成功点击了验证按钮
                if not submit_success:
                    logger.warning("未能找到并点击验证按钮，验证可能失败")
                    return False
                
            except Exception as e:
                logger.error(f"点击验证按钮失败: {e}")
                return False
            
            # 等待验证结果
            time.sleep(3)
            
            # 完成任务
            VerificationManager.update_verification_status(task_id, {
                "status": "success",
                "message": "验证码验证成功"
            })
            
            # 发送成功通知
            try:
                success_message = {
                    "type": "verification_success",
                    "task_id": task_id,
                    "message": "验证码验证成功"
                }
                
                # 通过Redis发布成功通知
                publish_result = publish_ws_message("verification", success_message)
                if publish_result:
                    logger.info(f"成功通知已通过Redis发布，任务ID: {task_id}")
                else:
                    logger.error(f"成功通知Redis发布失败，任务ID: {task_id}")
                
                logger.info(f"验证成功: {success_message}")
            except Exception as e:
                logger.error(f"发送成功通知失败: {e}")
            
            # 清理任务
            VerificationManager.remove_verification_task(task_id)
            logger.info("手机验证码验证完成")
            
            return True
        except (NoSuchElementException, TimeoutException) as e:
            logger.info(f"尝试找验证码输入框时出错: {e}")
            # 进一步检查是否真的不需要验证码
            try:
                # 检查页面中是否包含需要验证码的标志
                needs_verification = driver.execute_script("""
                return document.body.innerText.includes('验证码') || 
                       document.body.innerHTML.includes('验证码') ||
                       document.getElementById('yodaVerification') !== null ||
                       document.getElementById('yodaSmsCodeBtn') !== null;
                """)
                
                if needs_verification:
                    logger.warning("页面包含验证码相关元素，但找不到验证码输入框，可能需要人工介入")
                    return False
                else:
                    logger.info("确认无需手机验证码")
                    return True
            except Exception as check_err:
                logger.error(f"检查验证码需求时出错: {check_err}")
                return False
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
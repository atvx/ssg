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
    logger.info("===== 开始账号密码登录流程 =====")
    
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
    
    logger.info(f"使用账号: {username} 进行登录")
    
    # 切换到登录iframe
    for retry in range(3):  # 重试3次
        try:
            # 等待页面加载
            time.sleep(5)  # 增加等待时间
            
            # 查找登录iframe
            logger.info("查找登录iframe...")
            iframe_present = False
            for iframe_retry in range(5):  # 尝试5次查找iframe
                try:
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    if iframes:
                        iframe_present = True
                        logger.info(f"找到 {len(iframes)} 个iframe")
                        break
                    else:
                        logger.warning(f"未找到iframe, 重试 {iframe_retry+1}/5")
                        time.sleep(2)
                except Exception as e:
                    logger.warning(f"查找iframe出错: {e}")
                    time.sleep(2)
            
            if not iframe_present:
                logger.warning("未找到登录iframe，尝试刷新页面")
                driver.refresh()
                time.sleep(5)
                continue
            
            login_iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
            
            # 切换到登录iframe
            driver.switch_to.frame(login_iframe)
            time.sleep(2)  # 增加等待时间
        
            # 检查当前iframe是否包含登录表单
            login_form_present = driver.execute_script("""
                return document.getElementById('login') !== null || 
                       document.querySelector('.ep-tab_item') !== null;
            """)
            
            if not login_form_present:
                logger.warning("当前iframe中未找到登录表单，尝试切换回主文档并重试")
                driver.switch_to.default_content()
                time.sleep(2)
                continue
        
            # 切换到账号登录tab
            try:
                tab_elements = driver.find_elements(By.CSS_SELECTOR, ".ep-tab_item")
                account_tab = None
                
                for tab in tab_elements:
                    if "账号登录" in tab.text:
                        account_tab = tab
                        break
                
                if account_tab:
                    logger.info("找到账号登录标签，点击切换")
                    account_tab.click()
                    time.sleep(2)
                else:
                    logger.warning("未找到账号登录标签，尝试使用默认登录方式")
            except Exception as e:
                logger.warning(f"切换到账号登录标签时出错: {e}")
            
            # 勾选协议复选框
            try:
                checkbox_elements = driver.find_elements(By.CSS_SELECTOR, ".ep-checkbox-container")
                if checkbox_elements:
                    logger.info("找到协议复选框，点击勾选")
                    checkbox_elements[0].click()
                    time.sleep(1)
            except Exception as e:
                logger.warning(f"勾选协议复选框时出错: {e}")
            
            # 输入账号
            try:
                username_field = wait.until(EC.presence_of_element_located((By.ID, "login")))
                username_field.clear()
                time.sleep(1)
                for char in username:
                    username_field.send_keys(char)
                    time.sleep(0.1)
                logger.info("已输入账号")
            except Exception as e:
                logger.error(f"输入账号时出错: {e}")
                driver.switch_to.default_content()
                continue
            
            # 输入密码
            try:
                password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
                password_field.clear()
                time.sleep(1)
                for char in password:
                    password_field.send_keys(char)
                    time.sleep(0.1)
                logger.info("已输入密码")
            except Exception as e:
                logger.error(f"输入密码时出错: {e}")
                driver.switch_to.default_content()
                continue
            
            # 点击登录按钮
            try:
                login_buttons = driver.find_elements(By.CSS_SELECTOR, ".ep-login_btn")
                if login_buttons:
                    logger.info("找到登录按钮，点击登录")
                    login_buttons[0].click()
                    time.sleep(3)  # 增加等待时间
                else:
                    # 尝试使用JavaScript点击
                    logger.warning("未找到登录按钮，尝试使用JavaScript点击")
                    driver.execute_script("""
                        var buttons = document.querySelectorAll('button');
                        for (var i = 0; i < buttons.length; i++) {
                            if (buttons[i].textContent.includes('登录')) {
                                buttons[i].click();
                                return true;
                            }
                        }
                        return false;
                    """)
                    time.sleep(3)  # 增加等待时间
            except Exception as e:
                logger.error(f"点击登录按钮时出错: {e}")
                driver.switch_to.default_content()
                continue
            
            # 处理滑块验证
            try:
                logger.info("检查是否需要处理滑块验证...")
                handle_iframe_slider(driver, wait)
                time.sleep(2)  # 增加等待时间
            except Exception as e:
                logger.warning(f"处理滑块验证时出错: {e}")
            
            # 处理手机验证码验证
            time.sleep(2)
            try:
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
                    time.sleep(2)  # 增加等待时间
            except Exception as e:
                logger.warning(f"检查手机验证码验证时出错: {e}")
            
            # 返回主框架
            try:
                driver.switch_to.default_content()
                time.sleep(3)  # 增加等待时间
            except Exception as e:
                logger.warning(f"返回主框架时出错: {e}")
            
            # 检查登录状态
            login_success = False
            try:
                # 先等待页面加载完成
                time.sleep(5)  # 增加等待时间
                
                # 获取当前URL
                current_url = driver.current_url
                logger.info(f"登录后的当前URL: {current_url}")
                
                # 截取登录页面以便调试
                try:
                    screenshot_path = "/tmp/login_debug.png"
                    driver.save_screenshot(screenshot_path)
                    logger.info(f"保存了登录调试截图: {screenshot_path}")
                except Exception as e:
                    logger.warning(f"保存截图出错: {e}")
                
                # 尝试通过URL判断是否登录成功
                if "selectorg" in current_url or "/web/rms-account/#/auth" not in current_url:
                    login_success = True
                    logger.info("基于URL判断登录成功")
                
                # 尝试查找登录后常见的元素
                if not login_success:
                    success_elements = driver.find_elements(By.CSS_SELECTOR, ".org-profile, .user-profile, .username, .logout")
                    if success_elements:
                        login_success = True
                        logger.info(f"找到登录成功元素: {len(success_elements)}个")
                        
                # 检查本地存储和cookie中的令牌
                if not login_success:
                    token_exists = driver.execute_script("""
                    return document.cookie.indexOf('token') > -1 || 
                           document.cookie.indexOf('auth') > -1 ||
                           window.localStorage.getItem('token') !== null;
                    """)
                    if token_exists:
                        login_success = True
                        logger.info("通过cookie/localStorage令牌判断登录成功")
                
                # 使用JavaScript检查是否成功
                if not login_success:
                    js_check = driver.execute_script("""
                    // 检查URL
                    if (window.location.href.indexOf('selectorg') > -1) return true;
                    
                    // 检查DOM元素
                    var profileElements = document.querySelectorAll('.org-profile, .user-profile, .username, .logout');
                    if (profileElements.length > 0) return true;
                    
                    // 检查是否不在登录页
                    var loginForm = document.querySelector('#login, .ep-login_btn');
                    return loginForm === null;
                    """)
                    
                    if js_check:
                        login_success = True
                        logger.info("通过JavaScript检查判断登录成功")
            except Exception as e:
                logger.error(f"检查登录状态时出错: {e}")
                
            if login_success:
                logger.info("登录成功")
                return True
            else:
                logger.warning(f"第{retry+1}次登录尝试未成功，准备重试")
                driver.refresh()
                time.sleep(5)  # 增加等待时间
        except Exception as e:
            logger.error(f"登录过程中出现异常: {e}")
            try:
                driver.switch_to.default_content()
                time.sleep(2)
                driver.refresh()
                time.sleep(5)
            except:
                pass
    
    logger.error("多次尝试登录失败")
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
                # 使用精确路径找到手机号
                try:
                    phone_elem = driver.find_element(By.XPATH, "//div[@id='popup-context']//span[contains(@class, '_sms__mobile')]")
                    if phone_elem:
                        phone_number = phone_elem.text
                        logger.info(f"找到手机号: {phone_number}")
                except Exception:
                    # 如果XPath失败，使用JavaScript提取
                    phone_number = driver.execute_script("""
                    // 尝试精确定位手机号元素
                    var mobileContainer = document.querySelector('div[class*="_sms__wrapper"] span[class*="_sms__mobile"]');
                    if (mobileContainer) {
                        return mobileContainer.textContent.trim();
                    }
                    
                    // 查找整个弹窗内容
                    var popupContext = document.getElementById('popup-context');
                    if (popupContext) {
                        var content = popupContext.textContent;
                        var matches = content.match(/\\d+\\*+\\d+/);
                        if (matches) {
                            return matches[0];
                        }
                    }
                    return "";
                    """)
                    if phone_number:
                        logger.info(f"通过JavaScript找到手机号: {phone_number}")
                
                # 如果前两种方法都失败，从页面源代码提取
                if not phone_number:
                    page_source = driver.page_source
                    import re
                    phone_matches = re.findall(r'\d{2,3}\*{3,}\d{2,3}', page_source)
                    if phone_matches:
                        phone_number = phone_matches[0]
            except Exception as e:
                logger.warning(f"获取手机号时出错: {e}")
            
            # 如果没有获取到手机号，使用备用值
            if not phone_number:
                phone_number = "未知手机号"
                logger.warning("未能获取到手机号，使用默认值")
            else:
                phone_number = phone_number.strip()
            
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
                # 使用纯JavaScript方法处理验证码输入和按钮点击
                result = driver.execute_script(f"""
                try {{
                    // 找到验证码输入框
                    var input = document.getElementById('yodaVerification');
                    if (!input) {{
                        // 如果找不到指定ID，尝试使用CSS选择器
                        input = document.querySelector('input[placeholder="请输入验证码"]');
                    }}
                    
                    if (!input) {{
                        return {{"success": false, "error": "找不到验证码输入框"}};
                    }}
                    
                    // 设置验证码值
                    input.value = '{verification_code}';
                    
                    // 触发必要的事件
                    ['input', 'change'].forEach(function(eventType) {{
                        var event = new Event(eventType, {{ bubbles: true }});
                        input.dispatchEvent(event);
                    }});
                    
                    // 找到验证按钮
                    var btn = document.getElementById('yodaSubmit');
                    if (!btn) {{
                        // 备用方法找按钮
                        btn = document.querySelector('button[type="button"][id="yodaSubmit"]');
                    }}
                    
                    if (!btn) {{
                        return {{"success": false, "error": "找不到验证按钮"}};
                    }}
                    
                    // 移除禁用状态
                    btn.disabled = false;
                    btn.removeAttribute('disabled');
                    
                    // 移除包含banAutoSubmit的所有类
                    if (btn.className) {{
                        btn.className = btn.className.split(' ').filter(function(cls) {{
                            return !cls.includes('banAutoSubmit');
                        }}).join(' ');
                    }}
                    
                    // 等待很短的时间确保事件处理完成
                    setTimeout(function() {{
                        btn.click();
                    }}, 100);
                    
                    return {{"success": true, "message": "验证码已输入并点击验证按钮"}};
                }} catch (e) {{
                    return {{"success": false, "error": e.toString()}};
                }}
                """)
                
                if result and result.get('success'):
                    logger.info(f"JavaScript成功处理验证码: {verification_code}")
                    logger.info(f"结果: {result.get('message')}")
                    # 给页面一些时间处理验证
                    time.sleep(2)
                    submit_success = True
                else:
                    error_msg = result.get('error') if result else "未知错误"
                    logger.warning(f"JavaScript处理验证码失败: {error_msg}")
                    
                    # 尝试使用更简单的JavaScript方法
                    simple_result = driver.execute_script(f"""
                    try {{
                        // 尝试不同的选择器定位验证码输入框
                        var selectors = [
                            '#yodaVerification',
                            'input[placeholder="请输入验证码"]',
                            'input[class*="smsCodeInput"]',
                            'input[type="number"]'
                        ];
                        
                        var input = null;
                        for (var i = 0; i < selectors.length; i++) {{
                            input = document.querySelector(selectors[i]);
                            if (input) break;
                        }}
                        
                        if (!input) return false;
                        
                        // 设置值
                        input.value = '{verification_code}';
                        
                        // 查找按钮
                        var btnSelectors = [
                            '#yodaSubmit',
                            'button[id="yodaSubmit"]',
                            '.btnWrapper button',
                            'button[type="button"]:not([id="yodaSmsCodeBtn"])'
                        ];
                        
                        var btn = null;
                        for (var j = 0; j < btnSelectors.length; j++) {{
                            btn = document.querySelector(btnSelectors[j]);
                            if (btn) break;
                        }}
                        
                        if (!btn) return false;
                        
                        // 启用按钮
                        btn.disabled = false;
                        btn.removeAttribute('disabled');
                        
                        // 点击按钮
                        setTimeout(function() {{
                            btn.click();
                        }}, 200);
                        
                        return true;
                    }} catch(e) {{
                        console.error(e);
                        return false;
                    }}
                    """)
                    
                    if simple_result:
                        logger.info("备用JavaScript方法成功处理验证码")
                        time.sleep(2)
                        submit_success = True
                    else:
                        logger.error("所有JavaScript方法都失败，无法处理验证码")
                        return False
            except Exception as e:
                logger.error(f"处理验证码过程出错: {e}", exc_info=True)
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
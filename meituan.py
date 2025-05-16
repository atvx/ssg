from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
import time
import random
import json
import re
import os
import pickle
from seleniumwire import webdriver as wire_webdriver
from seleniumwire.utils import decode
from decimal import Decimal, ROUND_HALF_UP
from tqdm import tqdm
import datetime
import subprocess
import platform

# 配置常量
CONFIG = {
    "LOGIN_URL": "https://pos.meituan.com/web/rms-account#/login",
    "BUSINESS_OVERVIEW_URL": "https://pos.meituan.com/web/report/business-report?_fe_report_use_storage_query=true#/rms-report/business-report",
    "PHONE_NUMBER": "13884950903",
    "TARGET_ORG": "叁石哥丰都麻辣鸡",
    "API_TIMEOUT": 30,
    "MONITOR_SCOPES": [
        r'https://pos\.meituan\.com/.*/tree/paged/query\?',
        r'https://pos\.meituan\.com/web/api/v2/reports/combine/business-summary-page'
    ],
    "WAIT_TIME": 15,
    "USER_DATA_DIR": "chrome_user_data",
    "COOKIES_FILE": os.path.join("chrome_user_data", "meituan_cookies.pkl")
}

# 滑块验证模式: 0=自动, 1=手动
SLIDER_VERIFY_MODE = 0
# 是否监控API响应
MONITOR_API_RESPONSE = True
# 登录方式: 0=手机号登录, 1=账号登录
LOGIN_MODE = 1

# 账号登录信息
ACCOUNT_CONFIG = {
    "USERNAME": "13884950903",
    "PASSWORD": "sanshige123456"
}


def init_chrome_driver(force_new_session=False):
    """初始化Chrome浏览器
    
    Args:
        force_new_session (bool): 如果为True，不使用现有的用户数据目录
    """
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # 使用用户数据目录保持登录状态
    use_user_data_dir = not force_new_session
    if use_user_data_dir:
        try:
            # 检查默认用户数据目录是否存在
            user_data_dir = os.path.abspath(CONFIG["USER_DATA_DIR"])
            if not os.path.exists(user_data_dir):
                os.makedirs(user_data_dir, exist_ok=True)
                print(f"创建用户数据目录: {user_data_dir}")
            
            # 使用固定目录
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        except Exception as e:
            print(f"设置用户数据目录时出错，将使用临时用户配置文件")
            use_user_data_dir = False
    else:
        print("使用新会话模式，不加载用户数据目录")
    
    # 抑制控制台错误消息
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--silent")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
    
    # 首次尝试启动浏览器
    try:
        if MONITOR_API_RESPONSE:
            seleniumwire_options = {
                'disable_encoding': True,
                'suppress_connection_errors': True
            }
            driver = wire_webdriver.Chrome(options=chrome_options, seleniumwire_options=seleniumwire_options)
            driver.scopes = CONFIG["MONITOR_SCOPES"]
        else:
            driver = webdriver.Chrome(options=chrome_options)
            
        # 防止检测
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        
        return driver
    except Exception as e:
        error_message = str(e).lower()
        
        # 检查是否是用户数据目录被占用的错误
        if "user data directory is already in use" in error_message and use_user_data_dir:
            print("检测到Chrome实例已在运行，正在尝试关闭...")
            
            # 尝试终止现有Chrome进程
            kill_chrome_processes()
            
            # 等待进程完全终止
            time.sleep(2)
            
            # 重新尝试启动Chrome，但不使用用户数据目录
            try:
                # 移除用户数据目录选项
                chrome_options = Options()
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option("useAutomationExtension", False)
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_argument("--log-level=3")
                chrome_options.add_argument("--silent")
                chrome_options.add_argument("--disable-logging")
                chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
                
                print("使用新会话模式启动Chrome...")
                
                if MONITOR_API_RESPONSE:
                    seleniumwire_options = {
                        'disable_encoding': True,
                        'suppress_connection_errors': True
                    }
                    driver = wire_webdriver.Chrome(options=chrome_options, seleniumwire_options=seleniumwire_options)
                    driver.scopes = CONFIG["MONITOR_SCOPES"]
                else:
                    driver = webdriver.Chrome(options=chrome_options)
                
                # 防止检测
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
                
                return driver
            except Exception as inner_e:
                raise Exception(f"无法启动Chrome: {inner_e}")
        else:
            # 其他类型的错误，抛出异常
            raise Exception(f"启动Chrome时出错: {e}")


def js_click(driver, selector):
    """通过JavaScript点击元素"""
    script = f"""
    const el = document.querySelector('{selector}');
    if (el) {{ 
        el.click(); 
        return true; 
    }}
    return false;
    """
    return driver.execute_script(script)


def hide_all_popups(driver):
    """隐藏所有类型的引导弹窗"""
    js_hide_tips = """
    var hiddenPopups = 0;
    // 隐藏report-Modal-Index-tips-PaZZV弹窗
    var tipsDiv = document.querySelector('.report-Modal-Index-tips-PaZZV[style*="display: block"]');
    if (tipsDiv) {
        tipsDiv.style.display = 'none';
        hiddenPopups++;
    }
    // 隐藏wrapperForCssHide弹窗
    var otherTipsDiv = document.querySelector('.wrapperForCssHide.cssShow[style*="display: block"]');
    if (otherTipsDiv) {
        otherTipsDiv.style.display = 'none';
        hiddenPopups++;
    }
    // 隐藏以org-menu-intro-mask-开头的class的div
    var maskDivs = document.querySelectorAll('div[class^="org-menu-intro-mask-"]');
    if (maskDivs && maskDivs.length > 0) {
        for (var i = 0; i < maskDivs.length; i++) {
            if (maskDivs[i].style.display !== 'none') {
                maskDivs[i].style.display = 'none';
                hiddenPopups++;
            }
        }
    }
    // 隐藏报表中心页面的引导弹窗
    var reportTipsDivs = document.querySelectorAll('div[class^="report-business-location-modal-tips-container-"]');
    if (reportTipsDivs && reportTipsDivs.length > 0) {
        for (var i = 0; i < reportTipsDivs.length; i++) {
            if (reportTipsDivs[i].style.display !== 'none') {
                reportTipsDivs[i].style.display = 'none';
                hiddenPopups++;
            }
        }
    }
    // 如果我们发现并隐藏了任何弹窗，确保所有的遮罩层也被隐藏
    if (hiddenPopups > 0) {
        var masks = document.querySelectorAll('.ant-modal-mask, .modal-mask, [class*="mask"]');
        for (var i = 0; i < masks.length; i++) {
            if (masks[i].style.display !== 'none' && masks[i].style.visibility !== 'hidden') {
                masks[i].style.display = 'none';
            }
        }
    }
    return hiddenPopups > 0;
    """
    try:
        return driver.execute_script(js_hide_tips)
    except Exception as e:
        print(f"处理引导弹窗时出错: {e}")
        return False


def simulate_human_drag(driver, target_distance=200):
    """简化的滑块拖动函数，使用直接的JavaScript实现"""
    print(f"尝试拖动滑块 距离: {target_distance}px")
    try:
        result = driver.execute_script("""
        // 查找滑块
        var box = document.getElementById('yodaBox') || document.querySelector('.boxStatic');
        if (!box) {
            console.log('未找到滑块元素');
            return false;
        }

        console.log('找到滑块元素');
        var rect = box.getBoundingClientRect();
        var startX = rect.left + 5;
        var startY = rect.top + rect.height / 2;
        
        // 模拟鼠标按下
        var mouseDown = new MouseEvent('mousedown', {
            bubbles: true,
            cancelable: true,
            view: window,
            clientX: startX,
            clientY: startY
        });
        box.dispatchEvent(mouseDown);
        
        // 等待20ms后开始移动
        setTimeout(function() {
            // 模拟鼠标移动
            for (var i = 1; i <= 20; i++) {
                (function(step) {
                    setTimeout(function() {
                        var moveX = startX + (arguments[0] / 20) * step;
                        var moveEvent = new MouseEvent('mousemove', {
                            bubbles: true,
                            cancelable: true,
                            view: window,
                            clientX: moveX,
                            clientY: startY + (Math.random() - 0.5) * 2
                        });
                        document.dispatchEvent(moveEvent);
                    }, step * 10);
                })(i);
            }
            
            // 移动完成后抬起鼠标
            setTimeout(function() {
                var mouseUp = new MouseEvent('mouseup', {
                                bubbles: true,
                                cancelable: true,
                                view: window,
                    clientX: startX + arguments[0],
                                clientY: startY
                });
                document.dispatchEvent(mouseUp);
            }, 220);
        }, 20);
        
        return true;
        """, target_distance)
        
        return result
    except Exception as e:
        print(f"模拟拖动滑块时出错: {e}")
        return False


def detect_slider_and_target(driver, wait):
    """检测滑块元素并估算需要滑动的距离"""
    try:
        # 使用JavaScript检测滑块元素，更可靠地获取信息
        slider_info = driver.execute_script("""
        var yodaBox = document.getElementById('yodaBox');
        var boxWrapper = document.getElementById('yodaBoxWrapper');
        
        if (!yodaBox || !boxWrapper) {
            // 查找可能的其他滑块元素
            var sliders = document.querySelectorAll('.boxStatic, [class*="slider"]');
            var wrappers = document.querySelectorAll('.box-wrapper, [class*="wrapper"]');
            
            if (sliders.length > 0 && wrappers.length > 0) {
                yodaBox = sliders[0];
                boxWrapper = wrappers[0];
            } else {
                return null;
            }
        }
        
        return {
            found: true,
            boxWidth: yodaBox.offsetWidth,
            wrapperWidth: boxWrapper.offsetWidth
        };
        """)
        
        if not slider_info or not slider_info.get('found'):
            return None, 0
            
        # 计算滑动距离
        slider_width = slider_info.get('boxWidth', 40)
        wrapper_width = slider_info.get('wrapperWidth', 300)
        target_distance = wrapper_width - slider_width - 5  # 减去一点偏移量
        
        # 找到滑块元素
        try:
            slider = driver.find_element(By.ID, "yodaBox")
        except Exception:
            try:
                slider = driver.find_element(By.CLASS_NAME, "boxStatic")
            except Exception:
                # 尝试查找其他可能的滑块元素
                sliders = driver.find_elements(By.CSS_SELECTOR, "[class*='slider'], [class*='box']")
                if sliders:
                    slider = sliders[0]
                else:
                    return None, 0
        
        return slider, target_distance
    except Exception as e:
        print(f"检测滑块元素时出错: {e}")
        return None, 0


def handle_slider_verification(driver, wait):
    """处理滑块验证码，使用简化的方法"""
    print("开始检查滑块验证...")
    
    # 检查是否有滑块验证弹窗
    has_verification = False
    try:
        # 输出当前页面源码中的关键元素，用于调试
        page_source = driver.page_source
        if "请向右拖动滑块" in page_source or "yodaBox" in page_source:
            print("页面源码中检测到滑块验证相关内容")
            has_verification = True
        
        # 直接检查滑块元素
        try:
            has_slider = driver.execute_script("""
            var mask = document.getElementById('yodaPopupMask');
            var slider = document.getElementById('yodaBox') || document.querySelector('.boxStatic') || document.querySelector('[class*=slider]');
            
            return mask && mask.style.display === 'flex' && slider !== null;
            """)
            
            if has_slider:
                print("通过JavaScript检测到滑块验证")
                has_verification = True
        except Exception:
            pass
    except Exception:
        pass
    
    if not has_verification:
        print("没有检测到滑块验证")
        return
    
    print("检测到滑块验证码")

    if SLIDER_VERIFY_MODE == 1:  # 手动模式
        print("=" * 50)
        print("请手动操作滑块完成验证，操作完成后按回车继续...")
        input()
    else:  # 自动模式
        print("使用自动模式完成滑块验证...")
        
        try:
            # 获取滑块宽度和轨道宽度
            slider_info = driver.execute_script("""
            var slider = document.getElementById('yodaBox') || document.querySelector('.boxStatic');
            var wrapper = document.getElementById('yodaBoxWrapper') || document.querySelector('.box-wrapper');
            
            if (slider && wrapper) {
                return {
                    sliderWidth: slider.clientWidth,
                    wrapperWidth: wrapper.clientWidth
                };
            }
            
            // 如果找不到标准元素，尝试一些启发式方法获取尺寸
            var sliders = document.querySelectorAll('[class*=slider], [class*=box]');
            var wrappers = document.querySelectorAll('[class*=wrapper]');
            
            if (sliders.length > 0 && wrappers.length > 0) {
                return {
                    sliderWidth: sliders[0].clientWidth || 40,
                    wrapperWidth: wrappers[0].clientWidth || 300
                };
            }
            
            return {sliderWidth: 40, wrapperWidth: 300};
            """)
            
            slider_width = slider_info.get('sliderWidth', 40)
            wrapper_width = slider_info.get('wrapperWidth', 300)
            
            # 计算需要滑动的距离
            target_distance = wrapper_width - slider_width - 5
            print(f"计算滑动距离: 轨道宽度 {wrapper_width}px - 滑块宽度 {slider_width}px = {target_distance}px")
            
            # 多次尝试不同的滑动距离
            success = False
            distances = [
                target_distance,
                target_distance * 0.95,
                wrapper_width * 0.8,
                wrapper_width * 0.9,
                wrapper_width - 50
            ]
            
            for i, distance in enumerate(distances):
                print(f"尝试 {i+1}/{len(distances)}: 滑动距离 {distance:.1f}px")
                simulate_human_drag(driver, distance)
                
                # 等待验证结果
                time.sleep(2)
                
                # 检查验证是否通过
                try:
                    verification_passed = driver.execute_script("""
                    var mask = document.getElementById('yodaPopupMask');
                    return !mask || mask.style.display !== 'flex';
                    """)
                    
                    if verification_passed:
                        print("滑块验证成功!")
                        success = True
                        break
                    
                    print("验证未通过，尝试下一个距离")
                    time.sleep(1)
                except Exception:
                    print("检查验证状态时出错")
            
            # 如果自动滑动失败，提示手动操作
            if not success:
                print("自动滑动滑块失败，请手动完成验证")
                input("请手动完成验证，然后按回车继续...")
        except Exception as e:
            print(f"处理滑块验证过程中出错: {e}")
            input("请手动完成验证，然后按回车继续...")


def monitor_api_response(driver, target_api_url, max_wait_time=30, output_file=None, callback=None, methods=None, start_time=None):
    """监控并获取API响应数据"""
    if not (MONITOR_API_RESPONSE and hasattr(driver, 'requests')):
        print(f"API监控未启用或driver不支持监控")
        return None
    
    monitor_start_time = time.time()
    api_response_data = None
    processed_request_ids = set()
    
    while not api_response_data and (time.time() - monitor_start_time) < max_wait_time:
        for req in driver.requests:
            if id(req) in processed_request_ids:
                continue
                
            processed_request_ids.add(id(req))
            
            # 时间戳过滤
            if start_time and hasattr(req, 'date') and req.date:
                req_time = req.date.timestamp()
                if req_time < start_time:
                    continue
            
            # URL匹配
            url_matched = re.search(target_api_url, req.url) or (target_api_url in req.url)
                
            # 请求方法匹配
            method_matched = not methods or req.method in methods
                
            if req.response and url_matched and method_matched:
                try:
                    resp_raw = decode(req.response.body,
                                   req.response.headers.get('Content-Encoding', 'identity'))
                    resp_json = json.loads(resp_raw.decode('utf-8'))
                    
                    api_response_data = resp_json
                    
                    if output_file:
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(resp_json, f, ensure_ascii=False, indent=2)
                    
                    if callback and callable(callback):
                        callback(resp_json)
                    
                    break
                except Exception as parse_e:
                    print(f"解析API响应时出错: {parse_e}")
        
        if api_response_data:
            break
            
        # 等待
        elapsed_time = time.time() - monitor_start_time
        remaining_time = max_wait_time - elapsed_time
        
        if remaining_time > 0:
            time.sleep(1)
        else:
            print(f"等待超时 ({max_wait_time}秒)，停止监控")
    
    return api_response_data


def login_with_phone(driver, wait):
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
            for char in CONFIG["PHONE_NUMBER"]:
                phone_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.1))
        except Exception:
            try:
                phone_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='输入手机号']")))
                phone_field.clear()
                for char in CONFIG["PHONE_NUMBER"]:
                    phone_field.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.1))
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
            time.sleep(random.uniform(0.05, 0.1))
    
        # 点击登录按钮
        login_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "ep-login_btn")))
        login_button.click()
        
        # 处理可能出现的滑块验证（使用handle_iframe_slider代替handle_slider_verification）
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


def login_with_account(driver, wait):
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
            time.sleep(random.uniform(0.05, 0.1))
        
        # 输入密码
        password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
        password_field.clear()
        for char in ACCOUNT_CONFIG["PASSWORD"]:
            password_field.send_keys(char)
            time.sleep(random.uniform(0.05, 0.1))
        
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
            return True
        else:
            print("登录可能未成功，请检查页面状态")
            return False
    except Exception as e:
        print(f"登录过程出现异常: {e}")
        return False


def handle_iframe_slider(driver, wait):
    """在iframe内处理滑块验证"""
    # 等待加载
    time.sleep(2)
        
    # 检查是否出现滑块验证
    try:
        slider_box = None
        slider_title = None
        
        # 查找滑块元素
        try:
            slider_box = driver.find_element(By.ID, "yodaBox")
        except Exception:
            try:
                slider_box = driver.find_element(By.CLASS_NAME, "boxStatic")
            except Exception:
                # 寻找包含"请向右拖动滑块"文本的元素
                try:
                    slider_title = driver.find_element(By.XPATH, "//*[contains(text(), '请向右拖动滑块')]")
                except Exception:
                    pass
        
        # 如果找到滑块元素，进行处理
        if slider_box or slider_title:
            print("需要进行滑块验证")
            
            if SLIDER_VERIFY_MODE == 1:  # 手动模式
                print("=" * 50)
                print("请手动操作滑块完成验证，操作完成后按回车继续...")
                input()
                return True
            
            # 获取滑块和轨道尺寸
            slider_info = driver.execute_script("""
            var sliderBox = document.getElementById('yodaBox') || document.querySelector('.boxStatic');
            var track = document.getElementById('yodaBoxWrapper') || document.querySelector('.box-wrapper');
            
            if (!sliderBox || !track) {
                return {success: false, error: '未找到滑块或轨道元素'};
            }
            
            return {
                success: true,
                sliderWidth: sliderBox.offsetWidth || 40,
                trackWidth: track.offsetWidth || 300,
                sliderLeft: sliderBox.getBoundingClientRect().left,
                trackLeft: track.getBoundingClientRect().left
            };
            """)
            
            if not slider_info.get('success'):
                return False
            
            # 计算滑动距离
            slider_width = slider_info.get('sliderWidth', 40)
            track_width = slider_info.get('trackWidth', 300)
            distance = track_width - slider_width
            
            # 多次尝试不同距离
            distances = [
                distance,
                distance * 0.95,
                distance * 0.9,
                distance * 0.85,
                distance * 0.98
            ]
            
            for i, dist in enumerate(distances):
                # 执行滑动
                try:
                    # 直接使用JavaScript操作滑块
                    driver.execute_script("""
                    function simulateDrag(distance) {
                        var box = document.getElementById('yodaBox') || document.querySelector('.boxStatic');
                        if (!box) return false;
                        
                        var rect = box.getBoundingClientRect();
                        var startX = rect.left + 5;
                        var startY = rect.top + rect.height / 2;
                        
                        // 鼠标按下
                        var mouseDown = new MouseEvent('mousedown', {
                            bubbles: true,
                            cancelable: true,
                            view: window,
                            clientX: startX,
                            clientY: startY
                        });
                        box.dispatchEvent(mouseDown);
                        
                        // 记录步数和时间
                        var steps = 20;
                        var duration = 300;  // 总时间ms
                        var stepDelay = duration / steps;
                        
                        // 创建动画函数
                        var moveSlider = function(step) {
                            if (step >= steps) {
                                // 最后一步 - 鼠标释放
                                var mouseUp = new MouseEvent('mouseup', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window,
                                    clientX: startX + distance,
                                    clientY: startY
                                });
                                document.dispatchEvent(mouseUp);
                                return;
                            }
                            
                            // 计算当前位置 - 使用缓动函数
                            var ratio = step / steps;
                            var easeOutQuad = ratio * (2 - ratio);  // 缓动函数
                            var currentDistance = distance * easeOutQuad;
                            
                            // 添加一些随机性
                            var yOffset = (Math.random() - 0.5) * 2;
                            
                            // 创建鼠标移动事件
                            var mouseMove = new MouseEvent('mousemove', {
                                bubbles: true,
                                cancelable: true,
                                view: window,
                                clientX: startX + currentDistance,
                                clientY: startY + yOffset
                            });
                            document.dispatchEvent(mouseMove);
                            
                            // 递归调用下一步
                            setTimeout(function() {
                                moveSlider(step + 1);
                            }, stepDelay);
                        };
                        
                        // 开始移动
                        setTimeout(function() {
                            moveSlider(0);
                        }, 50);
                        
                        return true;
                    }
                    
                    return simulateDrag(arguments[0]);
                    """, dist)
                    
                    # 等待验证结果
                    time.sleep(2)
                    
                    # 检查滑块是否还存在
                    try:
                        still_has_slider = driver.execute_script("""
                        return document.getElementById('yodaBox') !== null || 
                               document.querySelector('.boxStatic') !== null || 
                               document.querySelector('.yoda-slider-wrapper') !== null;
                        """)
                        
                        if not still_has_slider:
                            print("滑块验证成功！")
                            return True
                    except Exception:
                        # 如果脚本执行出错，检查页面是否已跳转
                        return True
                except Exception:
                    pass
            
            # 如果所有尝试都失败，提示手动操作
            print("自动滑动失败，请手动操作")
            print("=" * 50)
            print("请手动操作滑块完成验证，操作完成后按回车继续...")
            input()
            return True
            
    except Exception as e:
        print(f"处理滑块验证时出错: {e}")
        # 提示手动操作
        print("=" * 50)
        print("请手动完成验证（如果需要），然后按回车继续...")
        input()
    
    return True


def handle_phone_verification(driver, wait):
    """处理手机验证码验证"""
    # 等待验证界面完全加载
    time.sleep(2)
    
    # 确认是否存在手机验证界面
    verify_elements = driver.execute_script("""
    var elements = {
        mask: document.getElementById('yodaPopupMask'),
        title: document.getElementById('yodaTitle'),
        input: document.getElementById('yodaVerification'),
        button: document.getElementById('yodaSmsCodeBtn')
    };
    
    return {
        hasMask: elements.mask !== null && elements.mask.style.display === 'flex',
        hasTitle: elements.title !== null && elements.title.textContent.includes('验证手机'),
        hasInput: elements.input !== null,
        hasButton: elements.button !== null
    };
    """)
    
    if not (verify_elements.get('hasMask') and (verify_elements.get('hasTitle') or verify_elements.get('hasInput'))):
        return True
    
    # 获取要发送验证码的手机号
    phone_number = driver.execute_script("""
    var phoneElem = document.querySelector('.verify-phone');
    if (phoneElem) {
        return phoneElem.textContent.replace(/[^0-9]/g, '');
    }
    return '';
    """)
    
    if phone_number:
        print(f"需要向手机号 {phone_number} 发送验证码")
    
    # 尝试点击获取验证码按钮
    get_code_success = driver.execute_script("""
    var btnId = document.getElementById('yodaSmsCodeBtn');
    var btnSelector = document.querySelector('button[class*="smsCodeBtn"]');
    var btnText = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('获取验证码'));
    
    var btn = btnId || btnSelector || btnText;
    if (btn && !btn.disabled) {
        btn.click();
        return true;
    }
    return false;
    """)
    
    if get_code_success:
        print("=" * 50)
        print("验证码已发送到手机，请注意查收")
        verify_code = input("请输入收到的验证码: ")
        
        # 输入验证码
        input_success = driver.execute_script(f"""
        var inputId = document.getElementById('yodaVerification');
        var inputSelector = document.querySelector('input[placeholder="请输入验证码"]');
        var inputType = document.querySelector('input[type="number"]');
        
        var input = inputId || inputSelector || inputType;
        if (input) {{
            input.value = '{verify_code}';
            // 触发input事件使验证按钮可用
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            // 触发change事件
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return true;
        }}
        return false;
        """)
        
        if input_success:
            # 等待验证按钮变为可用状态
            for i in range(10):
                button_enabled = driver.execute_script("""
                var btn = document.getElementById('yodaSubmit');
                return btn && !btn.disabled;
                """)
                
                if button_enabled:
                    break
                    
                time.sleep(0.5)
            
            # 尝试点击验证按钮
            submit_success = False
            for i in range(10):
                try:
                    submit_success = driver.execute_script("""
                    var btnId = document.getElementById('yodaSubmit');
                    var btnText = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('验证'));
                    
                    var btn = btnId || btnText;
                    if (btn) {
                        // 移除disabled属性
                        btn.disabled = false;
                        btn.click();
                        return true;
                    }
                    return false;
                    """)
                    
                    if submit_success:
                        # 等待验证结果
                        time.sleep(3)
                        
                        # 检查是否仍在验证界面
                        still_in_verify = driver.execute_script("""
                        var mask = document.getElementById('yodaPopupMask');
                        return mask && mask.style.display === 'flex';
                        """)
                        
                        if not still_in_verify:
                            # 登录成功，保存cookies
                            if hasattr(driver, 'get_cookies'):
                                save_cookies(driver)
                            return True
                        else:
                            # 检查是否有错误提示
                            error_msg = driver.execute_script("""
                            var tip = document.getElementById('yodaTip');
                            return tip ? tip.textContent : '';
                            """)
                            
                            if error_msg and "验证码" in error_msg and "错误" in error_msg:
                                print("验证码错误，请重新获取验证码")
                                return handle_phone_verification(driver, wait)
                except Exception:
                    pass
                
                time.sleep(0.5)
            
            if not submit_success:
                print("未能成功提交验证码，请手动完成验证")
                print("=" * 50)
                print("请手动完成验证，然后按回车继续...")
                input()
        else:
            print("未能成功输入验证码，请手动验证")
            print("=" * 50)
            print("请手动完成验证，然后按回车继续...")
            input()
    else:
        print("未能成功获取验证码，请手动验证")
        print("=" * 50)
        print("请手动完成验证，然后按回车继续...")
        input()
        
    # 验证完成后再次保存cookies
    if hasattr(driver, 'get_cookies'):
        save_cookies(driver)
        
    return True


def select_organization(driver, wait):
    """选择目标机构"""
    try:
        # 等待页面加载
        time.sleep(2)

        # 检查是否在选择机构页面
        if "selectorg" in driver.current_url:
            print(f"选择机构: {CONFIG['TARGET_ORG']}")
            
            # 使用JavaScript直接查找并点击目标机构
            js_code = f"""
            var found = false;
            var items = document.querySelectorAll('.org-item');
            for (var i = 0; i < items.length; i++) {{
                var nameDiv = items[i].querySelector('.name div:first-child');
                if (nameDiv && nameDiv.textContent.includes('{CONFIG['TARGET_ORG']}')) {{
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
                # print("成功选择机构")
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


def navigate_to_report_center(driver, wait):
    """导航到报表中心页面"""
    try:
        time.sleep(1)
        
        # 尝试多种方式找到并点击报表中心链接
        methods = [
            lambda: wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[@href='/web/report/main#/rms-report/home']"))).click(),
            lambda: wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[.//span[contains(text(), '报表中心')]]"))).click(),
            lambda: driver.execute_script("""
                var links = document.querySelectorAll('a');
                for (var i = 0; i < links.length; i++) {
                    if (links[i].textContent.includes('报表中心') || 
                        links[i].href.includes('/web/report/main') ||
                        links[i].getAttribute('href').includes('/web/report/main')) {
                        links[i].click();
                        return true;
                    }
                }
                return false;
            """)
        ]
        
        for method in methods:
            try:
                method()
                time.sleep(2)
                if "/web/report/" in driver.current_url:
                    # 隐藏可能的弹窗
                    for _ in range(2):
                        hide_all_popups(driver)
                        time.sleep(0.5)
                    return True
            except:
                continue
                
        print("无法导航到报表中心")
        return False
    except Exception as e:
        print(f"导航到报表中心失败: {e}")
        return False


def navigate_to_business_overview(driver, wait):
    """导航到营业概览页面并获取仓库列表"""
    try:
        # 确保在报表中心
        if "/web/report/" not in driver.current_url:
            navigate_to_report_center(driver, wait)
            
        # 直接导航到营业概览页面
        driver.get(CONFIG["BUSINESS_OVERVIEW_URL"])
        time.sleep(3)
        
        # 验证是否成功跳转
        if "business-report" in driver.current_url:
            # 隐藏弹窗
            for _ in range(2):
                hide_all_popups(driver)
                time.sleep(0.5)
                
            # 监控仓库列表API并处理数据
            def process_tree_query_response(resp_json):
                # 筛选含"仓"且不带括号的机构
                pattern = re.compile(r'^[^()（）]*仓[^()（）]*$')
                warehouses = [
                    item["orgName"]
                    for item in resp_json["data"]["items"]
                    if pattern.search(item.get("orgName", ""))
                ]
                
                # 选择日期
                # target_date = "2025-05-14"
                
                # 设置日期范围
                # print("设置查询日期范围...")
                # select_date(driver, target_date)
                # time.sleep(1)
                
                # 查询每个仓库销售数据
                print(f"查询所有仓库销售数据...")
                results = []
                
                # 使用tqdm创建进度条
                for name in tqdm(warehouses, desc="处理进度", unit="仓", ncols=100, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"):
                    result = perform_advanced_search(driver, wait, target_org=name)
                    results.append(result)
                
                # 保存结果到文件
                with open('warehouse_results.json', 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
            
            # 监控API
            monitor_api_response(
                driver,
                "/tree/paged/query",
                max_wait_time=CONFIG["API_TIMEOUT"],
                callback=process_tree_query_response,
                methods=['POST']
            )
            return True
        else:
            print("未能成功跳转到营业概览页面")
            return False
    except Exception as e:
        print(f"导航到营业概览页面失败: {e}")
        return False


def perform_advanced_search(driver, wait, target_org="重庆北部新区仓"):
    """执行高级查询并获取数据"""
    # 初始化返回结果
    result = {
        "name": target_org,
        "incomeAmt": 0,
        "salesCartCount": 0,
        "avgIncomeAmt": 0
    }
    
    try:
        # 清空请求记录并记录时间戳
        if hasattr(driver, 'requests'):
            driver.requests.clear()
        request_start_time = time.time()
            
        # 点击高级按钮
        if not js_click(driver, 'a.addon-a'):
            print("未找到'高级'按钮")
            return result
            
        # 等待弹窗出现
        time.sleep(1.5)
        
        # 清空已有选择
        js_click(driver, 'a.clear')
        
        # 展开所有门店
        js_expand_all = """
        function expandAllAntTreeNodes() {
            const closedSwitchers = document.querySelectorAll('.ant-tree-switcher_close');
            if (closedSwitchers.length === 0) return true;
            closedSwitchers.forEach(switcher => {
                switcher.click();
            });
            setTimeout(expandAllAntTreeNodes, 300);
            return false;
        }
        return expandAllAntTreeNodes();
        """
        
        # 尝试展开所有节点
        for i in range(10):
            if driver.execute_script(js_expand_all):
                break
            time.sleep(0.5)
        
        # 等待树形结构完全展开
        time.sleep(1)
        
        # 点击目标仓库
        target_clicked = driver.execute_script(f"""
        const targetNode = document.querySelector('span.ant-tree-node-content-wrapper[title="{target_org}"]');
        if (targetNode) {{
            targetNode.click();
            return true;
        }}
        return false;
        """)
        
        if not target_clicked:
            # 尝试更宽松的选择器
            target_clicked = driver.execute_script(f"""
            const allNodes = Array.from(document.querySelectorAll('span.ant-tree-node-content-wrapper'));
            const targetNode = allNodes.find(node => node.textContent.includes('{target_org}'));
            if (targetNode) {{
                targetNode.click();
                return true;
            }}
            return false;
            """)
            
            if not target_clicked:
                print(f"无法找到目标仓库: {target_org}")
                return result
        
        # 等待选择生效
        time.sleep(0.5)
        
        # 全选表格中的所有行
        driver.execute_script("""
        const headerCheckbox = document.querySelector('.ant-table-header .ant-table-selection-column input.ant-checkbox-input');
        if (headerCheckbox && !headerCheckbox.checked) {
            headerCheckbox.click();
        }
        """)

        # 点击确认按钮
        if not driver.execute_script("""
        const confirmBtn = [...document.querySelectorAll('.ant-modal-footer button.ant-btn-primary')].find(btn => 
            btn.textContent.replace(/\\s+/g, '').includes('确认'));
        if (confirmBtn) {
            confirmBtn.click();
            return true;
        }
        return false;
        """):
            print("未找到'确认'按钮")
            return result

        # 更新时间戳，记录点击查询前的时间
        query_start_time = time.time()

        # 点击查询按钮
        if not driver.execute_script("""
        const queryBtn = [...document.querySelectorAll('button.ant-btn-primary')].find(btn => btn.textContent.trim() === '查询');
        if (queryBtn) {
            queryBtn.click();
            return true;
        }
        return false;
        """):
            print("未找到'查询'按钮")
            return result
        
        # 等待查询结果加载
        time.sleep(2)
        
        # 获取营业概览数据
        summary_data = monitor_api_response(
            driver,
            "https://pos.meituan.com/web/api/v2/reports/combine/business-summary-page",
            max_wait_time=CONFIG["API_TIMEOUT"],
            methods=['POST', 'GET'],
            start_time=query_start_time
        )

        # 提取业务数据
        if summary_data and 'data' in summary_data:
            try:
                # 获取数据
                business_compose = summary_data['data'].get('BusinessOverviewPrintBusinessCompose', {})
                business_rank = summary_data['data'].get('BusinessOverviewBusinessRank', {})
                
                # 收入金额
                incomeAmt = 0
                try:
                    compose_str = business_compose.get('data', '{}')
                    # 检查是否为空字符串
                    if compose_str == '':
                        compose_str = '{}'
                    compose_data = json.loads(compose_str)
                    items = compose_data.get('items', [])
                    if items and len(items) > 0:
                        # 安全获取金额，确保是数值
                        raw_amount = items[0].get('businessAmt', 0) # incomeAmt -> businessAmt
                        if isinstance(raw_amount, (int, float)):
                            incomeAmt = raw_amount / 100
                        else:
                            # 尝试转换为数值
                            try:
                                if raw_amount and raw_amount.strip():
                                    incomeAmt = float(raw_amount) / 100
                            except (ValueError, AttributeError):
                                print(f"无法转换金额值: {raw_amount}")
                                incomeAmt = 0
                except Exception as e:
                    print(f"处理收入金额数据时出错: {e}")
                
                # 销售项数量(车辆)
                salesCartCount = 0
                try:
                    rank_str = business_rank.get('data', '[]')
                    # 检查是否为空字符串
                    if rank_str == '':
                        rank_str = '[]'
                    rank_items = json.loads(rank_str)
                    if isinstance(rank_items, list):
                        salesCartCount = len(rank_items)
                except Exception as e:
                    print(f"处理销售数量数据时出错: {e}")
                
                # 计算平均收入
                if salesCartCount > 0 and incomeAmt > 0:
                    avgIncomeAmt = (Decimal(incomeAmt) / Decimal(salesCartCount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                else:
                    avgIncomeAmt = Decimal('0.00')
                
                # 更新返回结果
                result["incomeAmt"] = float(incomeAmt)
                result["salesCartCount"] = salesCartCount
                result["avgIncomeAmt"] = float(avgIncomeAmt)
                
            except Exception as e:
                print(f"解析业务数据时出错: {e}")
                # 打印更详细的错误信息
                import traceback
                print(traceback.format_exc())
                
        return result
        
    except Exception as e:
        print(f"执行高级查询时出错: {e}")
        # 打印更详细的错误信息
        import traceback
        print(traceback.format_exc())
        return result


def set_ant_date_picker(driver, start_date, end_date, input_index=0):
    """
    直接注入JS设置Ant Design日期范围控件的值
    start_date, end_date: 格式为YYYY-MM-DD
    input_index: 如果页面多个范围控件，通过索引选择，默认第一个
    """
    # 日期格式转换为控件要求的格式，如：2025/05/11
    start_date_formatted = start_date.replace('-', '/')
    end_date_formatted = end_date.replace('-', '/')

    # JS脚本，设置日期并触发事件
    script = f"""
    const inputs = document.querySelectorAll('.ant-calendar-picker-input');
    inputs[{input_index * 2}].removeAttribute('readonly');
    inputs[{input_index * 2}].value = '{start_date_formatted}';
    inputs[{input_index * 2}].dispatchEvent(new Event('input', {{ bubbles: true }}));
    inputs[{input_index * 2}].dispatchEvent(new Event('change', {{ bubbles: true }}));

    inputs[{input_index * 2 + 1}].removeAttribute('readonly');
    inputs[{input_index * 2 + 1}].value = '{end_date_formatted}';
    inputs[{input_index * 2 + 1}].dispatchEvent(new Event('input', {{ bubbles: true }}));
    inputs[{input_index * 2 + 1}].dispatchEvent(new Event('change', {{ bubbles: true }}));
    """
    driver.execute_script(script)
    print(f"日期范围设置为: {start_date} 至 {end_date}")


def select_date(driver, date_str):
    """
    在日期范围选择器中设置开始和结束日期为同一天
    
    参数:
        driver: Selenium WebDriver实例
        date_str: 日期字符串，格式为'YYYY-MM-DD'
    """
    # 将输入的日期字符串转换为日期对象
    target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
    target_year = target_date.year
    target_month = target_date.month
    target_day = target_date.day
    
    # 获取日期输入框
    date_inputs = driver.find_elements(By.CSS_SELECTOR, "input.ant-calendar-picker-input")
    if len(date_inputs) < 1:
        raise Exception("找不到日期选择器")
    
    # 尝试更可靠的方式设置日期
    try:
        # 使用JS直接设置日期值
        set_ant_date_picker(driver, date_str, date_str)
        time.sleep(1)
        # 尝试点击查询按钮以应用日期
        driver.execute_script("""
        const queryBtn = [...document.querySelectorAll('button.ant-btn-primary')].find(btn => btn.textContent.trim() === '查询');
        if (queryBtn) {
            queryBtn.click();
            return true;
        }
        return false;
        """)
        return
    except Exception as e:
        print(f"使用JS设置日期失败，尝试手动操作: {e}")
    
    # 以下是备用的手动操作方式
    # 1. 设置开始日期
    date_inputs[0].click()
    time.sleep(0.5)
    
    # 处理开始日期选择
    calendar = driver.find_element(By.CSS_SELECTOR, "div.ant-calendar-panel")
    
    # 获取当前显示的年份和月份
    year_select = calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-year-select")
    month_select = calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-month-select")
    
    # 安全地获取年份和月份文本
    year_text = year_select.text.replace('年', '')
    month_text = month_select.text.replace('月', '')
    
    # 检查并转换年份和月份
    try:
        current_year = int(year_text) if year_text.strip() else datetime.datetime.now().year
        current_month = int(month_text) if month_text.strip() else datetime.datetime.now().month
    except ValueError:
        print(f"无法解析年份或月份：年份='{year_text}'，月份='{month_text}'")
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month
    
    # 切换到目标年份
    while current_year != target_year:
        if current_year < target_year:
            calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-next-year-btn").click()
            current_year += 1
        else:
            calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-prev-year-btn").click()
            current_year -= 1
        time.sleep(0.2)
    
    # 切换到目标月份
    while current_month != target_month:
        if current_month < target_month:
            calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-next-month-btn").click()
            current_month = current_month + 1 if current_month < 12 else 1
        else:
            calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-prev-month-btn").click()
            current_month = current_month - 1 if current_month > 1 else 12
        time.sleep(0.2)
    
    # 找到并点击目标日期单元格
    day_cells = calendar.find_elements(By.CSS_SELECTOR, "td.ant-calendar-cell")
    for cell in day_cells:
        day_text = cell.text
        if day_text.isdigit() and int(day_text) == target_day:
            cell.click()
            break
    time.sleep(0.5)
    
    # 2. 设置结束日期（同样的日期）
    try:
        calendar = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.ant-calendar-panel"))
        )
        
        # 重复相同的步骤设置结束日期
        year_select = calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-year-select")
        month_select = calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-month-select")
        
        # 安全地获取年份和月份文本
        year_text = year_select.text.replace('年', '')
        month_text = month_select.text.replace('月', '')
        
        # 检查并转换年份和月份
        try:
            current_year = int(year_text) if year_text.strip() else datetime.datetime.now().year
            current_month = int(month_text) if month_text.strip() else datetime.datetime.now().month
        except ValueError:
            print(f"无法解析年份或月份：年份='{year_text}'，月份='{month_text}'")
            current_year = datetime.datetime.now().year
            current_month = datetime.datetime.now().month
        
        # 切换到目标年份
        while current_year != target_year:
            if current_year < target_year:
                calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-next-year-btn").click()
                current_year += 1
            else:
                calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-prev-year-btn").click()
                current_year -= 1
            time.sleep(0.2)
        
        # 切换到目标月份
        while current_month != target_month:
            if current_month < target_month:
                calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-next-month-btn").click()
                current_month = current_month + 1 if current_month < 12 else 1
            else:
                calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-prev-month-btn").click()
                current_month = current_month - 1 if current_month > 1 else 12
            time.sleep(0.2)
        
        # 找到并点击目标日期单元格
        day_cells = calendar.find_elements(By.CSS_SELECTOR, "td.ant-calendar-cell")
        for cell in day_cells:
            day_text = cell.text
            if day_text.isdigit() and int(day_text) == target_day:
                cell.click()
                break
    except Exception as e:
        print(f"设置结束日期时出错: {e}")
        # 尝试使用更简单的方式关闭日期选择器
        driver.execute_script("""
        document.body.click();
        """)


def save_cookies(driver):
    """保存cookies到文件"""
    try:
        if not driver:
            print("无法保存cookies: driver对象为空")
            return False
            
        cookies = driver.get_cookies()
        if not cookies:
            print("没有可保存的cookies")
            return False
            
        # 确保用户数据目录存在
        user_data_dir = os.path.abspath(CONFIG["USER_DATA_DIR"])
        if not os.path.exists(user_data_dir):
            os.makedirs(user_data_dir, exist_ok=True)
            print(f"创建用户数据目录: {user_data_dir}")
            
        # 保存cookie文件
        cookies_file = CONFIG["COOKIES_FILE"]
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


def load_cookies(driver, verify=True):
    """从文件加载cookies
    
    Args:
        driver: WebDriver实例
        verify: 是否验证cookies有效性
        
    Returns:
        bool: 是否成功加载有效cookies
    """
    try:
        cookies_file = CONFIG["COOKIES_FILE"]
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


def main():
    """主函数：执行完整的登录和数据获取流程"""
    print("启动美团POS自动化工具...")
    
    driver = None
    force_new_session = False
    retry_count = 0
    max_retries = 2
    
    while retry_count <= max_retries:
        try:
            # 初始化浏览器
            try:
                driver = init_chrome_driver(force_new_session)
                wait = WebDriverWait(driver, CONFIG["WAIT_TIME"])
            except Exception as e:
                # 简化错误输出，不显示详细堆栈信息
                if "user data directory is already in use" in str(e).lower():
                    # 这种错误已在init_chrome_driver中处理，但如果仍然失败，尝试强制新会话
                    print("无法自动关闭Chrome实例，尝试使用强制新会话模式...")
                    force_new_session = True
                    retry_count += 1
                    continue
                elif retry_count == 0:
                    # 首次尝试失败时不显示错误
                    print("浏览器初始化失败，尝试使用强制新会话模式...")
                    force_new_session = True
                    retry_count += 1
                    continue
                else:
                    # 最后一次尝试也失败时，提示用户手动解决
                    print("浏览器启动失败。请确保没有Chrome实例正在运行，然后重试。")
                    return
            
            # 打开登录页面
            driver.get(CONFIG["LOGIN_URL"])
            print("正在加载登录页面...")
            
            # 判断是否已经登录
            already_logged_in = False
            cookies_loaded = False
            
            # 只有在非强制新会话模式下才尝试加载cookie
            if not force_new_session:
                # 尝试加载cookies
                try:
                    cookies_loaded = load_cookies(driver, verify=True)
                    if cookies_loaded:
                        print("已加载之前的登录信息，尝试刷新页面...")
                        # 重新加载页面，检查是否已登录
                        driver.refresh()
                        time.sleep(3)
                except Exception as e:
                    print(f"加载cookies时出错: {e}")
                    cookies_loaded = False
                
                # 检查是否成功保持登录状态
                try:
                    if '/login' not in driver.current_url and '/auth' not in driver.current_url:
                        # 检查是否有个人信息元素
                        user_elements = driver.find_elements(By.CSS_SELECTOR, ".user-profile, .username, .logout, .org-profile")
                        
                        if user_elements:
                            print("使用之前的登录信息成功登录")
                            already_logged_in = True
                        else:
                            # 尝试更可靠的方式检测登录状态
                            logged_in = driver.execute_script("""
                            return document.cookie.indexOf('token') > -1 || 
                                   document.cookie.indexOf('auth') > -1 ||
                                   window.localStorage.getItem('token') !== null ||
                                   !window.location.href.includes('login');
                            """)
                            
                            if logged_in:
                                print("成功检测到登录状态")
                                already_logged_in = True
                except Exception as e:
                    print(f"检查登录状态时出错: {e}")
            
            # 如果没有成功登录，需要重新登录
            login_success = already_logged_in
            
            if not already_logged_in:
                # 如果之前尝试加载cookie但失败了，可能cookie已过期，尝试删除cookie文件
                if cookies_loaded == False and os.path.exists(CONFIG["COOKIES_FILE"]) and not force_new_session:
                    try:
                        # 备份旧cookie文件以防万一
                        cookies_file = CONFIG["COOKIES_FILE"]
                        backup_file = f"{cookies_file}.bak"
                        if os.path.exists(cookies_file):
                            import shutil
                            shutil.copy2(cookies_file, backup_file)
                            print(f"已备份旧cookie文件到: {backup_file}")
                        
                        # 删除可能过期的cookie
                        os.remove(cookies_file)
                        print("已删除可能过期的cookie文件")
                    except Exception as e:
                        print(f"删除cookie文件时出错: {e}")
                
                # 根据登录方式选择
                if LOGIN_MODE == 0:
                    print("使用手机号登录...")
                    login_success = login_with_phone(driver, wait)
                else:
                    print("使用账号密码登录...")
                    login_success = login_with_account(driver, wait)
                    
                # 如果登录成功，保存cookies以便下次使用
                if login_success:
                    save_cookies(driver)
                else:
                    # 如果登录失败且不是强制新会话，尝试使用新会话
                    if not force_new_session:
                        print("登录失败，尝试使用新会话模式...")
                        force_new_session = True
                        if driver:
                            driver.quit()
                            driver = None
                        retry_count += 1
                        continue
            
            if login_success:
                # 选择机构
                org_selected = False
                try:
                    org_selected = select_organization(driver, wait)
                    if org_selected:
                        print("机构选择成功")
                    else:
                        print("未能选择机构，但将继续执行")
                except Exception as e:
                    print(f"选择机构时出错: {e}")
                    
                # 无论机构选择是否成功，都尝试继续
                
                # 隐藏可能的弹窗
                try:
                    hide_all_popups(driver)
                except Exception:
                    pass
                
                # 导航到报表中心
                report_center_success = False
                try:
                    report_center_success = navigate_to_report_center(driver, wait)
                    if report_center_success:
                        print("成功导航到报表中心")
                    else:
                        print("无法导航到报表中心，但将继续尝试")
                except Exception as e:
                    print(f"导航到报表中心时出错: {e}")
                
                # 导航到营业概览并获取数据
                try:
                    navigate_to_business_overview(driver, wait)
                except Exception as e:
                    print(f"处理营业概览数据时出错: {e}")
                
                # 成功完成所需任务，跳出重试循环
                break
            else:
                print("登录失败")
                
                # 如果是最后一次重试，打印更详细的错误信息
                if retry_count == max_retries:
                    print("=" * 40)
                    print("诊断信息:")
                    cookies_file = os.path.relpath(CONFIG["COOKIES_FILE"])
                    user_data_dir = os.path.relpath(CONFIG["USER_DATA_DIR"])
                    print(f"- Cookie文件状态: {'存在' if os.path.exists(cookies_file) else '不存在'} ({cookies_file})")
                    print(f"- 用户数据目录状态: {'存在' if os.path.exists(user_data_dir) else '不存在'} ({user_data_dir})")
                    print("- 当前URL:", driver.current_url if driver else "无")
                    print("=" * 40)
                
                # 如果不是最后一次重试，尝试强制新会话模式
                if retry_count < max_retries:
                    print(f"尝试重新登录 (尝试 {retry_count+1}/{max_retries+1})")
                    force_new_session = True
                    if driver:
                        driver.quit()
                        driver = None
                    retry_count += 1
                    continue
                
                # 如果所有尝试都失败，提示用户重置环境
                print("所有登录尝试均失败，建议:")
                print("1. 关闭所有Chrome浏览器实例")
                print("2. 删除chrome_user_data目录和meituan_cookies.pkl文件")
                print("3. 重新运行程序")
                break
                
        except Exception as e:
            print(f"运行过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            
            # 如果不是最后一次重试，尝试使用新会话
            if retry_count < max_retries:
                print(f"尝试使用新会话重新运行 (尝试 {retry_count+1}/{max_retries+1})")
                force_new_session = True
                if driver:
                    driver.quit()
                    driver = None
                retry_count += 1
                continue
            else:
                break
        finally:
            # 每次重试之前，确保关闭之前的浏览器实例
            if driver and retry_count < max_retries and not login_success:
                driver.quit()
                driver = None
    
    # 等待用户确认后关闭浏览器
    if driver:
        try:
            input("处理完成，按回车键关闭浏览器...")
        except:
            pass
        finally:
            driver.quit()
    
    print("程序执行完成")


if __name__ == "__main__":
    main()
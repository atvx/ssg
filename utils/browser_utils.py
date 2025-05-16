import time
import re
import json
import random
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from seleniumwire.utils import decode


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


def handle_slider_verification(driver, wait, slider_verify_mode=0):
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

    if slider_verify_mode == 1:  # 手动模式
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


def handle_iframe_slider(driver, wait, slider_verify_mode=0):
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
            
            if slider_verify_mode == 1:  # 手动模式
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
                            # 登录成功
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
        
    return True


def monitor_api_response(driver, target_api_url, max_wait_time=30, output_file=None, callback=None, methods=None, start_time=None):
    """监控并获取API响应数据"""
    if not hasattr(driver, 'requests'):
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
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import re


def js_click(driver, selector, wait_time=5):
    """使用JavaScript点击元素，避免常规点击问题
    
    Args:
        driver: WebDriver实例
        selector: CSS选择器
        wait_time: 等待元素出现的最大时间
        
    Returns:
        bool: 点击成功返回True，否则返回False
    """
    try:
        # 等待元素出现
        WebDriverWait(driver, wait_time).until(
            lambda d: d.execute_script(f'return document.querySelector("{selector}") !== null')
        )
        
        # 使用JavaScript点击元素
        driver.execute_script(f'document.querySelector("{selector}").click();')
        return True
    except (TimeoutException, Exception) as e:
        return False


def monitor_api_response(driver, url_pattern, timeout=30, callback=None, methods=None):
    """监控页面API响应
    
    Args:
        driver: Selenium驱动器
        url_pattern: URL匹配模式
        timeout: 超时时间（秒）
        callback: 回调函数，接收响应数据作为参数
        methods: 要匹配的HTTP方法列表，例如 ['GET', 'POST']
        
    Returns:
        dict: API响应数据，超时返回None
    """
    try:
        # 如果driver没有_apiMonitor属性，初始化一个
        if not hasattr(driver, '_apiMonitor'):
            # 注入API监控脚本
            script = """
            // 创建API监控对象
            window._apiMonitor = {
                responses: {},
                observer: null
            };
            
            // 拦截XHR请求
            (function(open) {
                XMLHttpRequest.prototype.open = function(method, url) {
                    this._apiMonitorMethod = method;
                    this._apiMonitorUrl = url;
                    return open.apply(this, arguments);
                };
            })(XMLHttpRequest.prototype.open);
            
            (function(send) {
                XMLHttpRequest.prototype.send = function() {
                    var xhr = this;
                    xhr.addEventListener('load', function() {
                        try {
                            var responseText = xhr.responseText;
                            // 尝试解析JSON
                            if (responseText && responseText.trim() !== '') {
                                var jsonResponse = JSON.parse(responseText);
                                window._apiMonitor.responses[xhr._apiMonitorUrl] = {
                                    data: jsonResponse,
                                    method: xhr._apiMonitorMethod,
                                    timestamp: new Date().getTime()
                                };
                            }
                        } catch(e) {
                            // 忽略非JSON响应
                            console.log('API监控：无法解析响应', e);
                        }
                    });
                    return send.apply(this, arguments);
                };
            })(XMLHttpRequest.prototype.send);
            
            // 拦截Fetch请求
            (function(fetch) {
                window.fetch = function(url, options) {
                    return fetch.apply(this, [url, options]).then(function(response) {
                        // 克隆响应以便多次读取
                        var resClone = response.clone();
                        try {
                            resClone.json().then(function(jsonData) {
                                window._apiMonitor.responses[url] = {
                                    data: jsonData,
                                    method: options ? options.method || 'GET' : 'GET',
                                    timestamp: new Date().getTime()
                                };
                            });
                        } catch(e) {
                            // 忽略非JSON响应
                        }
                        return response;
                    });
                };
            })(window.fetch);
            """
            driver.execute_script(script)
            print("API监控已初始化")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # 获取当前所有记录的响应
            responses = driver.execute_script("return window._apiMonitor.responses;")
            
            # 检查是否有匹配的URL和方法
            for url, response in responses.items():
                # 改进的URL匹配逻辑，使用正则表达式以更灵活地匹配URL
                url_matched = url_pattern in url if isinstance(url_pattern, str) else bool(re.search(url_pattern, url))
                
                # 检查请求方法是否匹配
                method_matched = True
                if methods and response.get('method'):
                    method_matched = response.get('method').upper() in [m.upper() for m in methods]
                
                if url_matched and method_matched:
                    # 如果有回调函数，调用它
                    data = response.get('data')
                    if callback and callable(callback):
                        callback(data)
                    print(f"匹配到API响应: {url}")
                    return data
            
            time.sleep(0.5)
        
        # 超时时打印所有捕获的响应URLs，以便调试
        print(f"API监控超时({timeout}秒)，未找到匹配的响应。已捕获的URLs:")
        responses = driver.execute_script("return window._apiMonitor.responses;")
        for url in responses.keys():
            print(f" - {url}")
        
        return None
    except Exception as e:
        print(f"监控API响应出错: {e}")
        return None


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
            
            from config.settings import SLIDER_VERIFY_MODE
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


def hide_all_popups(driver):
    """隐藏页面中的所有弹窗
    
    Args:
        driver: WebDriver实例
        
    Returns:
        bool: 如果隐藏了任何弹窗则返回True，否则返回False
    """
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

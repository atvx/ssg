import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import re
import json
import logging

# 配置日志
logger = logging.getLogger(__name__)

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


def monitor_api_response(driver, url_pattern, timeout=30, callback=None, methods=None, payload_pattern=None, start_time=None):
    """监控页面API响应，使用selenium-wire捕获HTTP请求
    
    Args:
        driver: Selenium-Wire驱动器
        url_pattern: URL匹配模式
        timeout: 超时时间（秒）
        callback: 回调函数，接收响应数据作为参数
        methods: 要匹配的HTTP方法列表，例如 ['GET', 'POST']
        payload_pattern: 请求体匹配模式，字典类型，用于匹配请求正文中的关键字段
        start_time: 开始时间戳，只处理此时间之后的请求
        
    Returns:
        dict: API响应数据，超时返回None
    """
    try:
        # 确认是否使用的是selenium-wire的driver
        import inspect
        if 'seleniumwire' not in inspect.getmodule(driver.__class__).__name__:
            logger.warning("警告: 当前driver不是selenium-wire创建的，无法捕获HTTP请求")
            return None
        
        # 如果没有提供开始时间，使用当前时间
        if start_time is None:
            start_time = time.time()
            
        logger.info(f"开始监控API响应，URL模式: {url_pattern}, 超时时间: {timeout}秒")
        
        # 清除之前的请求记录
        try:
            driver.requests.clear()
        except Exception as e:
            logger.warning(f"清理请求记录时出错: {e}")
        
        monitor_start_time = time.time()
        check_interval = 0.5  # 检查间隔
        last_request_count = 0
        no_new_requests_count = 0
        max_no_new_requests = 10  # 如果连续10次检查都没有新请求，缩短超时
        
        while time.time() - monitor_start_time < timeout:
            try:
                # 获取所有请求
                current_requests = list(driver.requests)
                current_request_count = len(current_requests)
                
                # 检查是否有新请求
                if current_request_count == last_request_count:
                    no_new_requests_count += 1
                    if no_new_requests_count >= max_no_new_requests:
                        remaining_time = timeout - (time.time() - monitor_start_time)
                        if remaining_time > 30:  # 如果剩余时间超过30秒，缩短到30秒
                            logger.info(f"连续{max_no_new_requests}次检查无新请求，缩短超时时间到30秒")
                            timeout = (time.time() - monitor_start_time) + 30
                        no_new_requests_count = 0  # 重置计数器
                else:
                    no_new_requests_count = 0
                    logger.debug(f"检测到新请求: {current_request_count - last_request_count}个")
                
                last_request_count = current_request_count
                
                for request in current_requests:
                    if not request.response:
                        continue  # 跳过未完成的请求
                    
                    # 检查请求时间（如果可用）
                    if hasattr(request, 'date') and request.date:
                        req_timestamp = request.date.timestamp()
                        if req_timestamp < start_time:
                            logger.debug(f"跳过旧请求: {request.url}")
                            continue
                    
                    # 检查URL匹配
                    url_matched = url_pattern in request.url if isinstance(url_pattern, str) else bool(re.search(url_pattern, request.url))
                    
                    # 检查请求方法匹配
                    method_matched = True
                    if methods:
                        method_matched = request.method.upper() in [m.upper() for m in methods]
                    
                    # 检查请求体匹配
                    payload_matched = True
                    if payload_pattern and isinstance(payload_pattern, dict):
                        try:
                            request_body = request.body
                            if request_body:
                                if isinstance(request_body, bytes):
                                    request_body = request_body.decode('utf-8')
                                
                                if request_body.strip():
                                    try:
                                        request_payload = json.loads(request_body)
                                        for key, value in payload_pattern.items():
                                            if key not in request_payload or request_payload[key] != value:
                                                payload_matched = False
                                                break
                                    except json.JSONDecodeError:
                                        payload_matched = False
                                else:
                                    payload_matched = False
                            else:
                                payload_matched = False
                        except Exception as e:
                            logger.warning(f"解析请求体时出错: {e}")
                            payload_matched = False
                    
                    # 如果所有条件都匹配，返回响应体
                    if url_matched and method_matched and payload_matched:
                        try:
                            logger.info(f"匹配到API请求: {request.url} ({request.method})")
                            
                            # 解析响应体为JSON
                            response_body = request.response.body
                            if isinstance(response_body, bytes):
                                response_body = response_body.decode('utf-8')
                            
                            try:
                                response_data = json.loads(response_body)
                                response_time = time.time()
                                logger.info(f"API响应获取成功，耗时: {response_time - start_time:.2f}秒")
                                
                                # 如果有回调函数，调用它
                                if callback and callable(callback):
                                    try:
                                        callback(response_data)
                                    except Exception as e:
                                        logger.warning(f"回调函数执行失败: {e}")
                                
                                return response_data
                            except json.JSONDecodeError as e:
                                logger.warning(f"响应体解析JSON失败: {e}")
                                continue
                        except Exception as e:
                            logger.warning(f"处理响应时出错: {str(e)}")
                            continue
                
                # 等待一小段时间再检查
                time.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"监控过程中出错: {e}")
                time.sleep(check_interval)
        
        # 超时处理
        elapsed_time = time.time() - monitor_start_time
        logger.warning(f"API监控超时({elapsed_time:.1f}秒)，未找到匹配的响应")
        
        # 记录调试信息
        try:
            recent_requests = [req for req in driver.requests if req.response][-10:]  # 最近10个请求
            logger.debug(f"最近捕获的请求 ({len(recent_requests)}):")
            for i, request in enumerate(recent_requests):
                logger.debug(f"{i+1}. {request.method} {request.url}")
        except Exception as e:
            logger.debug(f"记录调试信息时出错: {e}")
        
        return None
        
    except Exception as e:
        logger.error(f"监控API响应出错: {str(e)}")
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

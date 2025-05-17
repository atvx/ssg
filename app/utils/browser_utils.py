import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


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


def monitor_api_response(driver, url_pattern, max_wait_time=30, methods=None, start_time=None):
    """监控并获取API响应
    
    Args:
        driver: WebDriver实例
        url_pattern: API URL或URL的一部分
        max_wait_time: 最大等待时间(秒)
        methods: HTTP方法列表，如['GET', 'POST']
        start_time: 开始监控的时间戳
        
    Returns:
        dict: API响应的JSON数据，如未捕获到则返回None
    """
    # 如果不是Selenium Wire的实例，或没有request记录功能，则返回None
    if not hasattr(driver, 'requests'):
        return None
    
    # 设置默认值
    if methods is None:
        methods = ['GET', 'POST']
    
    # 如果提供了开始时间，则只考虑该时间之后的请求
    if start_time is None:
        start_time = time.time()
    
    # 计算终止时间
    end_time = time.time() + max_wait_time
    
    # 等待匹配的请求出现
    while time.time() < end_time:
        for request in driver.requests:
            # 跳过不符合条件的请求
            if request.response is None:  # 请求尚未完成
                continue
                
            if request.method not in methods:  # 方法不匹配
                continue
                
            if url_pattern not in request.url:  # URL不匹配
                continue
                
            # 检查请求时间(如果可用)
            request_time = getattr(request, 'date', 0) or 0
            if request_time < start_time:
                continue
            
            # 如果响应体为空则跳过
            if not request.response.body:
                continue
            
            # 尝试解析JSON响应
            try:
                response_body = request.response.body.decode('utf-8')
                import json
                return json.loads(response_body)
            except Exception as e:
                continue
        
        # 短暂休眠避免CPU负载过高
        time.sleep(0.5)
    
    # 如果超时还未找到匹配的请求，则返回None
    return None

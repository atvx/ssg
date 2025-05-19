import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.browser_utils import js_click, hide_all_popups


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


def navigate_to_business_overview(driver, wait, config):
    """导航到营业概览页面并获取仓库列表"""
    try:
        # 确保在报表中心
        if "/web/report/" not in driver.current_url:
            navigate_to_report_center(driver, wait)
            
        # 直接导航到营业概览页面
        driver.get(config["BUSINESS_OVERVIEW_URL"])
        time.sleep(3)
        
        # 验证是否成功跳转
        if "business-report" in driver.current_url:
            # 隐藏弹窗
            for _ in range(2):
                hide_all_popups(driver)
                time.sleep(0.5)
                
            return True
        else:
            print("未能成功跳转到营业概览页面")
            return False
    except Exception as e:
        print(f"导航到营业概览页面失败: {e}")
        return False


def select_date(driver, date_str):
    """
    在日期范围选择器中设置开始和结束日期为同一天
    
    参数:
        driver: Selenium WebDriver实例
        date_str: 日期字符串，格式为'YYYY-MM-DD'
    """
    # 日期格式转换为控件要求的格式，如：2025/05/11
    date_formatted = date_str.replace('-', '/')

    # 直接注入JS设置Ant Design日期范围控件的值
    script = f"""
    const inputs = document.querySelectorAll('.ant-calendar-picker-input');
    inputs[0].removeAttribute('readonly');
    inputs[0].value = '{date_formatted}';
    inputs[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
    inputs[0].dispatchEvent(new Event('change', {{ bubbles: true }}));

    inputs[1].removeAttribute('readonly');
    inputs[1].value = '{date_formatted}';
    inputs[1].dispatchEvent(new Event('input', {{ bubbles: true }}));
    inputs[1].dispatchEvent(new Event('change', {{ bubbles: true }}));
    """
    driver.execute_script(script)
    print(f"日期范围设置为: {date_str}")
    
    # 尝试点击查询按钮以应用日期
    driver.execute_script("""
    const queryBtn = [...document.querySelectorAll('button.ant-btn-primary')].find(btn => btn.textContent.trim() === '查询');
    if (queryBtn) {
        queryBtn.click();
        return true;
    }
    return false;
    """)
    
    # 等待页面刷新
    time.sleep(2)


def select_date_range(driver, wait, start_date, end_date):
    """设置日期范围
    
    Args:
        driver: WebDriver实例
        wait: WebDriverWait实例
        start_date: 开始日期，格式为YYYY-MM-DD
        end_date: 结束日期，格式为YYYY-MM-DD
        
    Returns:
        bool: 是否成功设置日期范围
    """
    try:
        # 格式化日期，确保符合YYYY-MM-DD格式
        from datetime import datetime
        try:
            # 尝试解析日期字符串
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            
            # 转换为UI需要的格式
            start_date_ui = start_date_obj.strftime("%Y/%m/%d")
            end_date_ui = end_date_obj.strftime("%Y/%m/%d")
        except ValueError:
            print(f"无效的日期格式，需要YYYY-MM-DD。收到: start_date={start_date}, end_date={end_date}")
            return False
        
        # 使用直接的JavaScript方法设置日期选择器的值
        script = f"""
        function setDateRange(startDate, endDate) {{
            // 找到日期范围选择器
            const inputs = document.querySelectorAll('.ant-calendar-picker-input');
            if (!inputs || inputs.length < 2) {{
                console.error('未找到日期选择器输入框');
                return false;
            }}
            
            // 设置开始日期
            const startInput = inputs[0];
            startInput.value = '{start_date_ui}';
            startInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            startInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
            
            // 设置结束日期
            const endInput = inputs[1];
            endInput.value = '{end_date_ui}';
            endInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            endInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
            
            // 尝试自动点击查询按钮
            setTimeout(() => {{
                const queryBtn = [...document.querySelectorAll('button.ant-btn-primary')].find(btn => 
                    btn.textContent.trim() === '查询');
                if (queryBtn) {{
                    queryBtn.click();
                    console.log('自动点击了查询按钮');
                }}
            }}, 500);
            
            return true;
        }}
        
        return setDateRange('{start_date_ui}', '{end_date_ui}');
        """
        
        result = driver.execute_script(script)
        
        # 等待一下，确保日期选择生效
        import time
        time.sleep(2)
        
        print(f"日期范围设置: {start_date_ui} 至 {end_date_ui}, 结果: {'成功' if result else '失败'}")
        return result
    except Exception as e:
        print(f"设置日期范围时出错: {e}")
        return False 
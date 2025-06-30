import time
import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

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
        
    返回:
        bool: 设置日期成功返回True，失败返回False
    """
    try:
        # 将输入的日期字符串转换为日期对象
        target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        target_year = target_date.year
        target_month = target_date.month
        target_day = target_date.day
        
        print(f"设置日期: {date_str} (年:{target_year}, 月:{target_month}, 日:{target_day})")
        
        # 获取日期输入框
        date_inputs = driver.find_elements(By.CSS_SELECTOR, "input.ant-calendar-picker-input")
        if len(date_inputs) < 1:
            raise Exception("找不到日期选择器")
        
        # 1. 设置开始日期
        date_inputs[0].click()
        time.sleep(0.5)
        
        # 处理开始日期选择
        if not _set_calendar_date(driver, target_year, target_month, target_day):
            return False
        
        # 2. 设置结束日期（同样的日期）
        try:
            calendar = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.ant-calendar-panel"))
            )
            
            # 重复相同的步骤设置结束日期
            if not _set_calendar_date(driver, target_year, target_month, target_day):
                return False
                
            return True
        except Exception as e:
            print(f"设置结束日期时出错: {e}")
            # 尝试使用更简单的方式关闭日期选择器
            driver.execute_script("""
            document.body.click();
            """)
            return False
    except Exception as e:
        print(f"设置日期范围失败: {e}")
        return False


def _set_calendar_date(driver, target_year, target_month, target_day):
    """
    设置日历中的具体日期
    
    参数:
        driver: WebDriver实例
        target_year: 目标年份
        target_month: 目标月份
        target_day: 目标日期
        
    返回:
        bool: 设置成功返回True，失败返回False
    """
    try:
        calendar = driver.find_element(By.CSS_SELECTOR, "div.ant-calendar-panel")
        
        # 获取当前显示的年份和月份的函数
        def get_current_year_month():
            try:
                year_select = calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-year-select")
                month_select = calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-month-select")
                
                year_text = year_select.text.replace('年', '').strip()
                month_text = month_select.text.replace('月', '').strip()
                
                current_year = int(year_text) if year_text else datetime.datetime.now().year
                current_month = int(month_text) if month_text else datetime.datetime.now().month
                
                print(f"当前日历显示: {current_year}年{current_month}月")
                return current_year, current_month
            except (ValueError, NoSuchElementException) as e:
                print(f"获取当前年月失败: {e}")
                return datetime.datetime.now().year, datetime.datetime.now().month
        
        # 获取初始年月
        current_year, current_month = get_current_year_month()
        
        # 切换到目标年份
        max_year_attempts = 10  # 防止无限循环
        year_attempts = 0
        while current_year != target_year and year_attempts < max_year_attempts:
            if current_year < target_year:
                calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-next-year-btn").click()
            else:
                calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-prev-year-btn").click()
            
            time.sleep(0.3)
            current_year, current_month = get_current_year_month()
            year_attempts += 1
        
        if current_year != target_year:
            print(f"无法切换到目标年份 {target_year}，当前年份 {current_year}")
            return False
        
        # 切换到目标月份
        max_month_attempts = 24  # 最多尝试24次（2年的月份数）
        month_attempts = 0
        while current_month != target_month and month_attempts < max_month_attempts:
            if current_month < target_month:
                calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-next-month-btn").click()
            else:
                calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-prev-month-btn").click()
            
            time.sleep(0.3)
            # 重新获取当前年月，因为跨年时年份也会变化
            current_year, current_month = get_current_year_month()
            month_attempts += 1
            
            # 如果年份不对，需要重新调整年份
            if current_year != target_year:
                print(f"月份切换导致年份变化，重新调整年份从 {current_year} 到 {target_year}")
                year_diff = target_year - current_year
                if year_diff > 0:
                    for _ in range(abs(year_diff)):
                        calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-next-year-btn").click()
                        time.sleep(0.2)
                else:
                    for _ in range(abs(year_diff)):
                        calendar.find_element(By.CSS_SELECTOR, "a.ant-calendar-prev-year-btn").click()
                        time.sleep(0.2)
                
                # 重新获取年月
                current_year, current_month = get_current_year_month()
        
        if current_month != target_month or current_year != target_year:
            print(f"无法切换到目标日期 {target_year}年{target_month}月，当前 {current_year}年{current_month}月")
            return False
        
        print(f"成功切换到 {current_year}年{current_month}月，开始选择第{target_day}天")
        
        # 找到并点击目标日期单元格
        day_cells = calendar.find_elements(By.CSS_SELECTOR, "td.ant-calendar-cell")
        day_found = False
        for cell in day_cells:
            day_text = cell.text.strip()
            if day_text.isdigit() and int(day_text) == target_day:
                # 检查这个日期单元格是否可点击（不是灰色的其他月份日期）
                cell_classes = cell.get_attribute("class")
                if "ant-calendar-disabled-cell" not in cell_classes and "ant-calendar-last-month-cell" not in cell_classes and "ant-calendar-next-month-cell" not in cell_classes:
                    cell.click()
                    day_found = True
                    print(f"成功点击日期 {target_day}")
                    break
        
        if not day_found:
            print(f"未找到可点击的日期 {target_day}")
            return False
        
        time.sleep(0.5)
        return True
        
    except Exception as e:
        print(f"设置日历日期失败: {e}")
        return False

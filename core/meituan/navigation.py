import time
import datetime
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
        
    返回:
        bool: 设置日期成功返回True，失败返回False
    """
    try:
        # 将输入的日期字符串转换为日期对象
        target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        target_year = target_date.year
        target_month = target_date.month
        target_day = target_date.day
        
        # 获取日期输入框
        date_inputs = driver.find_elements(By.CSS_SELECTOR, "input.ant-calendar-picker-input")
        if len(date_inputs) < 1:
            raise Exception("找不到日期选择器")
        
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

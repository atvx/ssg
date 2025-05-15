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
from seleniumwire import webdriver as wire_webdriver
from seleniumwire.utils import decode
from decimal import Decimal, ROUND_HALF_UP
from tqdm import tqdm
import datetime

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
    "WAIT_TIME": 15
}

# 滑块验证模式: 0=自动, 1=手动
SLIDER_VERIFY_MODE = 0
# 是否监控API响应
MONITOR_API_RESPONSE = True


def init_chrome_driver():
    """初始化Chrome浏览器"""
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
    
    # 抑制控制台错误消息
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--silent")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
    
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


def simulate_human_drag(driver, slider, target_distance):
    """模拟人类拖动滑块的行为"""
    js_code = """
    function simulateDrag(target_distance) {
        var slider = document.getElementById('yodaBox');
        if (!slider) {
            return false;
        }

        var rect = slider.getBoundingClientRect();
        var startX = rect.left + rect.width/2;
        var startY = rect.top + rect.height/2;

        slider.dispatchEvent(new MouseEvent('mousedown', {
            bubbles: true,
            cancelable: true,
            view: window,
            clientX: startX,
            clientY: startY
        }));

        return new Promise(resolve => {
            setTimeout(() => {
                var steps = 12;  
                var stepDistance = target_distance / steps;
                var currentStep = 0;

                function moveStep() {
                    if (currentStep >= steps) {
                        document.dispatchEvent(new MouseEvent('mousemove', {
                            bubbles: true,
                            cancelable: true,
                            view: window,
                            clientX: startX + target_distance + 10,
                            clientY: startY
                        }));

                        setTimeout(() => {
                            document.dispatchEvent(new MouseEvent('mouseup', {
                                bubbles: true,
                                cancelable: true,
                                view: window,
                                clientX: startX + target_distance + 10,
                                clientY: startY
                            }));
                            resolve(true);
                        }, 50);
                        return;
                    }

                    var progress = currentStep / steps;
                    var currentDistance;

                    if (progress < 0.3) {
                        currentDistance = target_distance * (progress * 1.5) / steps * currentStep;
                    } else if (progress > 0.7) {
                        currentDistance = target_distance - (target_distance - stepDistance * currentStep) * 0.5;
                    } else {
                        currentDistance = stepDistance * currentStep;
                    }

                    if (currentStep == steps - 1) {
                        currentDistance = target_distance * 0.95;
                    }

                    var yOffset = (Math.random() - 0.5) * 1;

                    document.dispatchEvent(new MouseEvent('mousemove', {
                        bubbles: true,
                        cancelable: true,
                        view: window,
                        clientX: startX + currentDistance,
                        clientY: startY + yOffset
                    }));

                    currentStep++;
                    setTimeout(moveStep, 15);
                }

                moveStep();
            }, 50);
        });
    }

    return simulateDrag(arguments[0]);
    """
    try:
        driver.execute_async_script(js_code, target_distance)
        return True
    except Exception:
        return False


def detect_slider_and_target(driver, wait):
    """检测滑块元素并估算需要滑动的距离"""
    try:
        slider = wait.until(EC.presence_of_element_located((By.ID, "yodaBox")))
        try:
            box_wrapper = driver.find_element(By.ID, "yodaBoxWrapper")
            box_wrapper_width = box_wrapper.rect['width']
            target_distance = box_wrapper_width - slider.rect['width'] + 5
        except:
            target_distance = 300
        return slider, target_distance
    except Exception as e:
        print(f"检测滑块元素时出错: {e}")
        return None, 0


def handle_slider_verification(driver, wait):
    """处理滑块验证码"""
    try:
        slider = wait.until(EC.presence_of_element_located((By.ID, "yodaBox")))
        print("检测到滑块验证码")

        if SLIDER_VERIFY_MODE == 1:  # 手动模式
            print("=" * 50)
            print("请手动操作滑块完成验证，操作完成后按回车继续...")
            input()
        else:  # 自动模式
            print("使用自动模式完成滑块验证...")
            slider, target_distance = detect_slider_and_target(driver, wait)
            if slider and target_distance > 0:
                simulate_human_drag(driver, slider, target_distance)
                time.sleep(3)
            else:
                print("无法检测滑块元素或估算距离，请手动操作")
                input("请手动完成验证，然后按回车继续...")
    except:
        # 没有滑块验证码，继续执行
        pass


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
    # 切换到登录iframe
    iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
    driver.switch_to.frame(iframe)
    time.sleep(1)

    # 勾选协议复选框
    try:
        checkbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".ep-checkbox-container")))
        checkbox.click()
    except Exception as e:
        print(f"勾选协议复选框失败: {e}")

    # 输入手机号
    try:
        phone_field = wait.until(EC.presence_of_element_located((By.ID, "phone")))
        phone_field.clear()
        for char in CONFIG["PHONE_NUMBER"]:
            phone_field.send_keys(char)
            time.sleep(random.uniform(0.05, 0.1))
    except Exception as e:
        print(f"输入手机号失败: {e}")
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
    try:
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
    except Exception as e:
        print(f"获取或输入验证码失败: {e}")
        return False

    # 点击登录按钮
    try:
        login_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "ep-login_btn")))
        login_button.click()
        
        # 处理可能出现的滑块验证
        time.sleep(1.5)
        handle_slider_verification(driver, wait)
        
        return True
    except Exception as e:
        print(f"点击登录按钮失败: {e}")
        return False


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


def main():
    """主函数：执行完整的登录和数据获取流程"""
    print("启动美团POS自动化工具...")
    
    driver = None
    try:
        # 初始化浏览器
        driver = init_chrome_driver()
        wait = WebDriverWait(driver, CONFIG["WAIT_TIME"])
        
        # 打开登录页面
        driver.get(CONFIG["LOGIN_URL"])
        print("正在加载登录页面...")
        
        # 登录
        if login_with_phone(driver, wait):
            print("登录成功")
            
            # 选择机构
            if select_organization(driver, wait):
                print("机构选择成功")
                
                # 隐藏可能的弹窗
                hide_all_popups(driver)
                
                # 导航到报表中心
                if navigate_to_report_center(driver, wait):
                    print("成功导航到报表中心")
                    
                    # 导航到营业概览并获取数据
                    navigate_to_business_overview(driver, wait)
            
        # 等待用户确认
        input("处理完成，按回车键关闭浏览器...")
        
    except Exception as e:
        print(f"运行过程中发生错误: {e}")
    finally:
        # 关闭浏览器
        if driver:
            driver.quit()
    
    print("程序执行完成")


if __name__ == "__main__":
    main()
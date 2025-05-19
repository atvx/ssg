import time
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from tqdm import tqdm

from utils.browser_utils import js_click, monitor_api_response


def perform_advanced_search(driver, wait, target_org, config):
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
        
        # 记录查询开始时间，用于过滤API响应
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

        # 再次清空请求记录，确保只捕获当前查询的API响应
        if hasattr(driver, 'requests'):
            driver.requests.clear()
        
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
        
        # 记录当前仓库名称，用于验证API响应是否匹配
        current_warehouse = target_org
        
        # 获取营业概览数据
        summary_data = monitor_api_response(
            driver,
            "https://pos.meituan.com/web/api/v2/reports/combine/business-summary-page",
            max_wait_time=config["API_TIMEOUT"],
            methods=['POST', 'GET'],
            start_time=query_start_time
        )

        # 验证API响应是否包含当前仓库信息
        if summary_data:
            print(f"获取到API响应数据，正在验证是否为仓库【{current_warehouse}】的数据...")
        
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
                
                # 打印调试信息
                print(f"仓库【{current_warehouse}】查询结果: 收入={incomeAmt}元, 销售={salesCartCount}辆")
                
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


def get_warehouse_list(driver, config):
    """获取所有仓库列表"""
    try:
        if not hasattr(driver, 'requests'):
            print("API监控未启用，无法获取仓库列表")
            return []
            
        # 清空请求缓存
        driver.requests.clear()
        
        # 监控API响应以获取仓库列表
        warehouses = []
        
        def process_tree_query_response(resp_json):
            nonlocal warehouses
            # 筛选含"仓"且不带括号的机构
            pattern = re.compile(r'^[^()（）]*仓[^()（）]*$')
            warehouses = [
                item["orgName"]
                for item in resp_json.get("data", {}).get("items", [])
                if pattern.search(item.get("orgName", ""))
            ]
            
        # 监控API
        monitor_api_response(
            driver,
            "/tree/paged/query",
            max_wait_time=config["API_TIMEOUT"],
            callback=process_tree_query_response,
            methods=['POST']
        )
        
        return warehouses
    except Exception as e:
        print(f"获取仓库列表时出错: {e}")
        return []


def get_all_meituan_data(driver, wait, config, target_date=None):
    """获取所有仓库销售数据"""
    # 获取所有仓库
    warehouses = get_warehouse_list(driver, config)
    
    if not warehouses:
        print("未能获取到仓库列表")
        return []
    
    # 设置日期范围（如果提供）
    if target_date:
        from .navigation import select_date
        select_date(driver, target_date)
    
    # 查询每个仓库销售数据
    print(f"查询所有仓库销售数据...")
    results = []
    
    # 使用tqdm创建进度条
    for name in tqdm(warehouses, desc="处理进度", unit="仓", ncols=100, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"):
        result = perform_advanced_search(driver, wait, target_org=name, config=config)
        results.append(result)
    
    # 保存结果到文件
    with open(config["OUTPUT_FILE"], 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    return results 
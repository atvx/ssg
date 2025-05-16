# 美团POS与多维数据获取工具

这个项目包含两个自动化工具，用于从不同来源获取销售数据：
1. `meituan.py` - 从美团POS系统获取销售数据
2. `duowei.py` - 从多维系统API获取销售数据

两个工具均可提取各仓库销售数据，适用于需要批量获取销售数据进行比对分析的商家。

## 功能特点

### 美团POS自动化工具 (meituan.py)

- 支持两种登录方式：
  - 手机号+验证码登录
  - 账号密码登录
- 自动/手动处理滑块验证码
- 自动处理手机验证码验证
- 自动选择指定机构（默认"叁石哥丰都麻辣鸡"）
- 自动隐藏各类引导弹窗
- 自动导航至报表中心和营业概览页面
- 批量提取所有仓库的销售数据
- 保存和加载cookies以维持登录状态
- 自动监控API响应，提取数据
- 结果保存到`sales_meituan.json`文件

### 多维系统数据获取工具 (duowei.py)

- 通过API直接获取仓库信息和销售数据
- 支持指定日期查询
- 自动计算每个仓库的销售统计数据
- 包含总销售额、有效车辆数和平均销售额
- 结果保存到`sales_duowei.json`文件

## 环境要求

- Python 3.6+
- Chrome浏览器 (仅meituan.py需要)
- Chrome WebDriver (仅meituan.py需要)
- 以下Python库：
  - selenium (meituan.py)
  - selenium-wire (meituan.py)
  - tqdm (meituan.py)
  - requests (duowei.py)

## 安装

```bash
pip install selenium selenium-wire tqdm requests
```

## 使用方法

### 美团POS自动化工具

1. 配置常量（CONFIG字典中）：
   - 修改手机号（PHONE_NUMBER）或账号密码（ACCOUNT_CONFIG）
   - 修改目标机构名称（TARGET_ORG）

2. 选择登录方式：
   ```python
   # 登录方式: 0=手机号登录, 1=账号登录
   LOGIN_MODE = 1
   ```

3. 运行脚本：
   ```bash
   python meituan.py
   ```

4. 交互提示：
   - 首次登录可能需要手动输入短信验证码
   - 如选择手动模式，需手动完成滑块验证

### 多维系统数据获取工具

1. 直接运行脚本（默认获取当天数据）：
   ```bash
   python duowei.py
   ```

2. 指定日期运行：
   ```bash
   python duowei.py 2024-05-14
   ```

## 配置选项

### 美团POS自动化工具

```python
# 滑块验证模式: 0=自动, 1=手动
SLIDER_VERIFY_MODE = 0
# 是否监控API响应
MONITOR_API_RESPONSE = True
# 登录方式: 0=手机号登录, 1=账号登录
LOGIN_MODE = 1

# 账号登录信息
ACCOUNT_CONFIG = {
    "USERNAME": "138****0903",
    "PASSWORD": "******"
}
```

## 输出结果格式

两个脚本生成的JSON文件格式相似，包含每个仓库的以下信息：

```json
[
  {
    "name": "仓库名称",
    "incomeAmt": 1234.56,      // 总收入金额
    "salesCartCount": 10,      // 销售数量/有效车辆数
    "avgIncomeAmt": 123.45     // 平均收入金额
  },
  // 更多仓库数据...
]
```

## 注意事项

- 美团POS工具首次运行时可能需要手动处理滑块验证
- 确保网络稳定，避免登录超时
- 短信验证码仍需手动输入
- API监控功能依赖于SeleniumWire库
- 可能需要定期更新，以适应系统变化
- 多维系统工具依赖API接口的稳定性
- 两个系统的数据可能存在差异，建议进行对比分析 
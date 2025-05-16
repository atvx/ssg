# 销售数据获取工具

这个项目是一个重构后的销售数据获取工具，可以从美团POS系统和多维系统获取销售数据，并将两个系统的数据合并。

## 项目结构

```
/Users/waino/dev/workspace/python/ssg/
│
├── config/                      # 配置模块
│   ├── __init__.py
│   └── settings.py              # 统一配置文件
│
├── core/                        # 核心功能模块
│   ├── __init__.py
│   ├── meituan/                 # 美团POS相关模块
│   │   ├── __init__.py
│   │   ├── auth.py              # 认证相关功能
│   │   ├── browser.py           # 浏览器操作相关功能
│   │   ├── navigation.py        # 页面导航相关功能
│   │   └── data.py              # 数据获取和处理功能
│   │
│   └── duowei/                  # 多维系统相关模块
│       ├── __init__.py
│       ├── api.py               # API交互功能
│       └── data.py              # 数据获取和处理功能
│
├── scripts/                     # 命令行工具脚本
│   ├── __init__.py
│   ├── meituan_cli.py           # 美团数据单独获取脚本
│   └── duowei_cli.py            # 多维数据单独获取脚本
│
├── utils/                       # 通用工具模块
│   ├── __init__.py
│   ├── browser_utils.py         # 浏览器操作工具
│   ├── data_utils.py            # 数据处理工具
│   └── file_utils.py            # 文件操作工具
│
├── main.py                      # 主入口文件，获取两个平台数据并合并
└── README.md                    # 项目文档
```

## 功能特点

### 美团POS自动化工具

- 支持两种登录方式：手机号+验证码或账号密码
- 自动/手动处理滑块验证码
- 自动选择指定机构
- 自动隐藏各类引导弹窗
- 自动导航至报表中心和营业概览页面
- 批量提取所有仓库的销售数据
- 保存和加载cookies维持登录状态

### 多维系统数据获取工具

- 通过API直接获取仓库信息和销售数据
- 支持指定日期查询
- 自动计算每个仓库的销售统计数据

### 数据合并功能

- 将两个系统的数据合并到一个列表中
- 支持按日期查询历史数据

## 环境要求

- Python 3.6+
- Chrome浏览器 (仅美团POS模块需要)
- Chrome WebDriver (仅美团POS模块需要)
- 以下Python库：
  - selenium
  - selenium-wire
  - tqdm
  - requests

## 安装

```bash
pip install selenium selenium-wire tqdm requests
```

## 使用方法

### 1. 获取所有平台数据并合并

```bash
python main.py [--date YYYY-MM-DD] [--output output_file.json]
```

参数说明：
- `--date`: 可选，指定查询日期，格式为YYYY-MM-DD。默认为当天。
- `--output`: 可选，指定合并后的输出文件名，默认为sales_merged.json。

### 2. 仅获取美团POS数据

```bash
# 使用main.py
python main.py --meituan [--date YYYY-MM-DD]

# 或直接使用CLI脚本
python -m scripts.meituan_cli [YYYY-MM-DD]
```

### 3. 仅获取多维系统数据

```bash
# 使用main.py
python main.py --duowei [--date YYYY-MM-DD]

# 或直接使用CLI脚本
python -m scripts.duowei_cli [YYYY-MM-DD]
```

## 配置选项

所有配置都集中在 `config/settings.py` 文件中：

### 美团POS配置

```python
MEITUAN_CONFIG = {
    "LOGIN_URL": "https://pos.meituan.com/web/rms-account#/login",
    "BUSINESS_OVERVIEW_URL": "...",
    "PHONE_NUMBER": "138****0903",
    "TARGET_ORG": "***",
    # ... 其他配置
}

# 滑块验证模式: 0=自动, 1=手动
SLIDER_VERIFY_MODE = 0

# 登录方式: 0=手机号登录, 1=账号登录
LOGIN_MODE = 1

# 账号登录信息
ACCOUNT_CONFIG = {
    "USERNAME": "138****0903",
    "PASSWORD": "******"
}
```

### 多维系统配置

```python
DUOWEI_CONFIG = {
    "BASE_URL": "http://saas.wxdw.top:8899/web_api",
    "USER_ID": "00016",
    "DB_NAME": "ssgmlj",
    "OUTPUT_FILE": "sales_duowei.json"
}
```

## 输出结果

- 美团数据: `sales_meituan.json`
- 多维数据: `sales_duowei.json`
- 合并数据: `sales_merged.json` (或通过--output参数指定)

### 合并数据格式示例：

```json
[
  {
    "incomeAmt": 1638.7,
    "salesCartCount": 7,
    "avgIncomeAmt": 234.1,
    "name": "***"
  },
  ...
]
```

## 注意事项

- 美团POS工具首次运行时可能需要手动处理滑块验证
- 确保网络稳定，避免登录超时
- 如使用手机验证码登录，需手动输入验证码
- 可能需要定期更新以适应系统变化 
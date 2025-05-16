import os

# 通用配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = BASE_DIR
CHROME_USER_DATA_DIR = os.path.join(BASE_DIR, "chrome_user_data")
COOKIES_FILE = os.path.join(CHROME_USER_DATA_DIR, "meituan_cookies.pkl")

# 美团POS配置
MEITUAN_CONFIG = {
    "LOGIN_URL": "https://pos.meituan.com/web/rms-account#/login",
    "BUSINESS_OVERVIEW_URL": "https://pos.meituan.com/web/report/business-report?_fe_report_use_storage_query=true#/rms-report/business-report",
    "PHONE_NUMBER": "13884950903",
    "TARGET_ORG": "叁石哥丰都麻辣鸡",
    "API_TIMEOUT": 30,
    "MONITOR_SCOPES": [
        r'https://pos\.meituan\.com/.*/tree/paged/query\?',
        r'https://pos\.meituan\.com/web/api/v2/reports/combine/business-summary-page'
    ],
    "WAIT_TIME": 15,
    "USER_DATA_DIR": CHROME_USER_DATA_DIR,
    "COOKIES_FILE": COOKIES_FILE,
    "OUTPUT_FILE": os.path.join(OUTPUT_DIR, "sales_meituan.json")
}

# 多维系统配置
DUOWEI_CONFIG = {
    "BASE_URL": "http://saas.wxdw.top:8899/web_api",
    "USER_ID": "00016",
    "DB_NAME": "ssgmlj",
    "OUTPUT_FILE": os.path.join(OUTPUT_DIR, "sales_duowei.json")
}

# 滑块验证模式: 0=自动, 1=手动
SLIDER_VERIFY_MODE = 0

# 是否监控API响应
MONITOR_API_RESPONSE = True

# 登录方式: 0=手机号登录, 1=账号登录
LOGIN_MODE = 1

# 账号登录信息
ACCOUNT_CONFIG = {
    "USERNAME": "13884950903",
    "PASSWORD": "sanshige123456"
} 
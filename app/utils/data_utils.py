import decimal
from datetime import datetime, date

def decimal_default(obj):
    """处理JSON序列化Decimal类型的默认函数"""
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

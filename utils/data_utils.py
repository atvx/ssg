from decimal import Decimal


def decimal_default(obj):
    """
    处理Decimal类型的JSON序列化
    """
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError("Object of type '%s' is not JSON serializable" % type(obj).__name__) 
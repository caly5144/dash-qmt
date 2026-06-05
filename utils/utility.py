import time as pytime

def millisecond_to_time(millis):
    """13位时间戳转换为时间格式字符串"""
    return pytime.strftime('%Y-%m-%d %H:%M:%S',pytime.localtime(millis/1000))

def safe_float(val):
    """安全转换浮点数，处理 None 和 NaN"""
    try:
        if val is None:
            return 0.0
        if isinstance(val, float) and math.isnan(val):
            return 0.0
        return float(val)
    except (ValueError, TypeError):
        return 0.0
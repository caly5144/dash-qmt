import time as pytime

def millisecond_to_time(millis):
    """13位时间戳转换为时间格式字符串"""
    return pytime.strftime('%Y-%m-%d %H:%M:%S',pytime.localtime(millis/1000))
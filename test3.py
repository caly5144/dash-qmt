# -*- coding: utf-8 -*-
from xtquant import xtdata
import time
from datetime import datetime

# ==========================================
# 1. 准备工作：获取今日日期字符串
# ==========================================
# 格式必须是 'YYYYMMDD' (例如 '20231216')
today_str = datetime.now().strftime("%Y%m%d")
print(f"📅 准备订阅今日 [{today_str}] 之后的全量数据")

# ==========================================
# 2. 回调函数
# ==========================================
def on_data(datas):
    for stock_code in datas:
        data_list = datas[stock_code]
        
        if data_list:
            # 这里的 data_list 就是从 start_time 开始到现在的所有数据列表
            # 第一次推送时，len(data_list) 会很大（比如下午3点时可能有240个数据）
            # 后续推送时，len(data_list) 通常会随时间增加或只推送增量（取决于具体版本机制，建议只取最后一个处理）
            
            # --- 场景A：处理最新的一根K线 (实时监控) ---
            latest = data_list[-1]
            time_str = time.strftime('%H:%M:%S', time.localtime(latest['time'] / 1000))
            print(f"🔔 [{stock_code}] 推送更新 | 时间: {time_str} | 收盘价: {latest['close']} | 当前列表长度: {len(data_list)}")
            
            # --- 场景B：如果需要处理当日全量历史 (比如计算移动平均线) ---
            # 你可以将 data_list 转为 DataFrame 进行计算
            # import pandas as pd
            # df = pd.DataFrame(data_list)
            # print(f"当前已积累当日K线 {len(df)} 根")

# ==========================================
# 3. 订阅逻辑
# ==========================================
# 这里使用中证500 ETF (510500.SH) 作演示，因为它既有1m数据又容易订阅成功
target_code = '510500.SH' 

print(f"正在发起订阅: {target_code} (1m)...")

subscribe_id = xtdata.subscribe_quote(
    stock_code=target_code, 
    period='1m',           # 指定 1分钟 K线
    start_time=today_str,  # 【关键】指定开始时间为今天 (格式 '20231216')
    end_time='',           # 结束时间为空，代表直到最新
    count=0,               # 配合 start_time 使用
    callback=on_data
)

print(f"订阅成功 ID: {subscribe_id}")
print("等待数据推送... (如果是盘中，第一次推送会包含开盘至今的所有K线)")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("程序结束")
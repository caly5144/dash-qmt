import time
import math
from datetime import datetime, timedelta
import pandas as pd
from peewee import fn, chunked
from xtquant import xtdata

from models.market_models import KlineData, market_db
from utils.utility import millisecond_to_time

xtdata.enable_hello = False

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

def get_target_codes():
    """获取标的代码列表"""
    # 建议注释掉下载板块，避免阻塞
    # xtdata.download_sector_data() 
    
    
    target_sectors = ['沪深A股', '沪深ETF', '沪深指数', '沪深转债', '北交所']
    all_codes = set()
    for sector in target_sectors:
        try:
            codes = xtdata.get_stock_list_in_sector(sector)
            if codes:
                all_codes.update(codes)
        except Exception as e:
            print(f"获取板块 {sector} 失败: {e}")
    return list(all_codes)

def get_last_update_map():
    """获取数据库中每个标的的最新日期"""
    try:
        # 注意这里使用的是新的 date 字段
        query = (KlineData
                 .select(KlineData.stock_code, fn.MAX(KlineData.date).alias('last_date'))
                 .group_by(KlineData.stock_code))
        
        return {item.stock_code: item.last_date for item in query}
    except Exception as e:
        print(f"查询数据库最新时间失败: {e}")
        return {}

def run_daily_sync_task():
    """执行日线数据增量同步"""
    print(f"【定时任务】开始执行日线数据同步 {datetime.now()}")
    
    period = '1d'
    stock_list = get_target_codes()
    if not stock_list:
        return

    # 1. 确定下载范围
    last_update_map = get_last_update_map()
    
    if not last_update_map:
        start_time_str = '20010101'
        print("【全量】数据库为空，下载起始日期: 20010101")
    else:
        # 增量模式：回推15天以防遗漏
        start_date = datetime.now() - timedelta(days=15)
        start_time_str = start_date.strftime('%Y%m%d')
        print(f"【增量】下载起始日期: {start_time_str}")

    # 2. 调用 QMT 下载数据到本地缓存
    print(f"正在下载 {len(stock_list)} 只标的数据...")
    xtdata.download_history_data2(stock_list, period=period, start_time=start_time_str)
    
    # 3. 读取本地数据并入库
    print("下载完成，开始处理入库...")
    
    batch_size = 50
    total_inserted = 0
    
    for i in range(0, len(stock_list), batch_size):
        batch_codes = stock_list[i : i + batch_size]
        
        # 使用 get_market_data_ex 读取，返回 {stock_code: DataFrame} 结构
        data_dict = xtdata.get_market_data_ex(
            stock_list=batch_codes, 
            period=period, 
            start_time=start_time_str,
            count=-1
        )
        
        rows_to_insert = []
        
        for code, df in data_dict.items():
            if df is None or df.empty:
                continue
            
            # 重置索引，确保 time 是一列数据
            df = df.reset_index()
            if 'time' not in df.columns and 'index' in df.columns:
                df.rename(columns={'index': 'time'}, inplace=True)

            db_last_date = last_update_map.get(code)
            
            for _, row in df.iterrows():
                # --- 时间戳转换修复 ---
                try:
                    raw_time = row['time']
                    # 13位时间戳 (毫秒)，例如 1765123200000
                    # 这里的判断阈值 1e11 约为 1973年，大于它通常是毫秒级时间戳
                    current_dt = millisecond_to_time(raw_time)[:10]
                except Exception:
                    continue

                # 增量过滤
                if db_last_date and current_dt <= db_last_date:
                    continue
                
                open_val = safe_float(row.get('open'))
                
                # 读取新字段 preClose, suspendFlag
                pre_close_val = safe_float(row.get('preClose'))
                suspend_val = int(safe_float(row.get('suspendFlag')))
                
                # 数据清洗
                if open_val == 0.0:
                    continue

                rows_to_insert.append({
                    'stock_code': code,
                    'date': current_dt, # 对应 models 中的 date 字段
                    'open': open_val,
                    'high': safe_float(row.get('high')),
                    'low': safe_float(row.get('low')),
                    'close': safe_float(row.get('close')),
                    'volume': int(safe_float(row.get('volume'))),
                    'amount': safe_float(row.get('amount')),
                    'pre_close': pre_close_val,
                    'suspend_flag': suspend_val
                })
        
        if rows_to_insert:
            with market_db.atomic():
                # 使用 chunked 分块插入
                for batch in chunked(rows_to_insert, 500):
                    KlineData.insert_many(batch).on_conflict_replace().execute()
            total_inserted += len(rows_to_insert)
            
        print(f"【进度】{min(i + batch_size, len(stock_list))}/{len(stock_list)}，累计入库 {total_inserted}")

    print(f"【完成】同步结束，新增 {total_inserted} 条")
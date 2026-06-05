import sys
sys.path.append('.')
sys.path.append('../..')

from utils.tushare_api import TushareAPI
from datetime import datetime
import pandas as pd
from peewee import Database
from models.market_models import DailyBasic, market_db


def sync_daily_basic():
    """
    优化后的股票每日指标数据同步函数 (基于交易日历)
    """
    print("开始检查数据库同步状态...")

    ta = TushareAPI()
    
    # 1. 获取数据库中已有的最晚日期
    latest_record = DailyBasic.select(DailyBasic.date).order_by(DailyBasic.date.desc()).first()
    
    if latest_record:
        latest_date_str = latest_record.date
        print(f"数据库中最新数据日期为: {latest_date_str}")
    else:
        latest_date_str = '20091231' # 设为前一天，以便第一天(20100101)能被选中
        print(f"数据库中无数据，将从默认日期 20100101 开始同步")
        
    today_str = datetime.now().strftime('%Y%m%d')

    # 2. 获取交易日历
    print("正在拉取交易日历...")
    try:
        # 调用你写好的交易日获取函数
        # 注意：如果你的函数支持传参，最好加上 ta.get_trade_date_df(start_date=latest_date_str, end_date=today_str)
        cal_df = ta.get_trade_date_df(start_date=latest_date_str) 
    except Exception as e:
        print(f"❌ 获取交易日历失败，请检查网络或接口: {e}")
        return

    # 3. 过滤出需要更新的有效交易日
    # 虽然你提到“返回的日期已经都是交易日了”，但为了绝对安全，这里还是加一层判断(如果有is_open字段)
    if 'is_open' in cal_df.columns:
        # 将其转为字符串判断，兼容 '1' 和 1
        cal_df = cal_df[cal_df['is_open'].astype(str) == '1']
        
    # 提取日历日期并进行筛选：晚于数据库最新日期，且早于或等于今天
    all_trade_dates = cal_df['cal_date'].astype(str).tolist()
    dates_to_sync = [d for d in all_trade_dates if latest_date_str < d <= today_str]
    
    # 确保日期是按时间正序排列的
    dates_to_sync.sort()

    if not dates_to_sync:
        print("🎉 数据已经是最新，没有新的交易日需要同步。")
        return

    print(f"共发现 {len(dates_to_sync)} 个交易日需要更新。开始逐日拉取...")

    # 4. 精确遍历每一个交易日进行同步
    for trade_date in dates_to_sync:
        print(f"正在同步交易日 [{trade_date}] 的数据...")
        
        try:
            df = ta.get_daily_basic_by_date(trade_date)
            
            if df is not None and not df.empty:
                data_to_insert = []
                
                # 遍历 DataFrame 处理空值与重命名
                for _, row in df.iterrows():
                    row_dict = {k: (None if pd.isna(v) else v) for k, v in row.items()}
                    
                    if 'ts_code' in row_dict:
                        row_dict['stock_code'] = row_dict.pop('ts_code')
                    if 'trade_date' in row_dict:
                        row_dict['date'] = row_dict.pop('trade_date')
                        
                    data_to_insert.append(row_dict)
                
                # 批量写入数据库
                if data_to_insert:
                    with market_db.atomic():
                        batch_size = 100
                        for i in range(0, len(data_to_insert), batch_size):
                            DailyBasic.insert_many(data_to_insert[i:i + batch_size]).execute()
                            
                    print(f"  └─ 成功入库 [{trade_date}] 数据 {len(data_to_insert)} 条。")
            else:
                # 理论上交易日历过滤后不会走到这里，除非接口当天数据尚未更新
                print(f"  └─ ⚠️ [{trade_date}] 虽然是交易日，但接口未返回数据 (可能今日数据尚未生成)。")
                
        except Exception as e:
            print(f"  └─ ❌ 同步 [{trade_date}] 时发生错误: {e}")
            # 如果你想遇到错误就停止本次同步，可以取消注释下面的 break
            # break 

    print("✅ 数据同步任务完成！")

if __name__ == "__main__":
    sync_daily_basic()
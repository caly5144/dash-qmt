import json
import tushare as ts
import pandas as pd
from configs.settings import DATA_DIR, GLOBAL_SECRETS


class TushareAPI:
    def __init__(self):
        self.token = GLOBAL_SECRETS.get('TUSHARE_API_TOKEN')
        self.pro = ts.pro_api(self.token)
    

    def get_trade_date_df(self, start_date: str, end_date: str=None):
        """获取交易日历"""
        df = self.pro.trade_cal(
            exchange='SSE',
            start_date=start_date,
            end_date=end_date
        )
        df = df.sort_values('cal_date')
        df = df[df['is_open'] == 1]
        return df

    def save_trade_date(self, start_date: str, end_date: str=None):
        """保存交易日历"""
        df = self.pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date)
        df = df.sort_values('cal_date')
        df = df[df['is_open'] == 1]
        df = df[['cal_date', 'is_open']].set_index('cal_date')
        df['id'] = list(range(len(df)))
        adict = df.to_dict()['id']
        with open(DATA_DIR / 'trade_date.json', 'w', encoding='utf-8') as f:
            json.dump(adict, f)
    

    def get_all_data_by_date(self, func, trade_date, once_nums=2000):
        '''获取某交易日所有数据通用方法'''
        this_nums = once_nums
        all_nums = 0
        frames = []
        while this_nums == once_nums:
            df = func(trade_date=trade_date, limit=once_nums, offset=all_nums)
            this_nums = len(df)
            all_nums += this_nums
            frames.append(df)
        return pd.concat(frames)

    def get_daily_basic_by_date(self, trade_date: str):
        """获取股票日线数据"""
        df = self.get_all_data_by_date(self.pro.daily_basic, trade_date)
        return df
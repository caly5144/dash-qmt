import json
import tushare as ts
from configs.settings import DATA_DIR, GLOBAL_SECRETS


class TushareAPI:
    def __init__(self):
        self.token = GLOBAL_SECRETS.get('TUSHARE_TOKEN')
        self.pro = ts.pro_api(self.token)
    
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
# -*- coding: utf-8 -*-
import time
from datetime import datetime

from utils.tushare_api import TushareAPI

if __name__ == '__main__':
    ts = TushareAPI()
    df = ts.get_daily_basic_by_date('20260604')
    print(df)
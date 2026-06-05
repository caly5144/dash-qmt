from peewee import CharField, FloatField, IntegerField, DateTimeField, CompositeKey
from . import market_db, MarketBaseModel

class KlineData(MarketBaseModel):
    """K线数据表"""
    stock_code = CharField()
    # period 字段已移除
    
    # start_time 重命名为 date
    date = CharField() 
    
    open = FloatField()
    high = FloatField()
    low = FloatField()
    close = FloatField()
    volume = IntegerField()
    amount = FloatField()
    
    # 新增字段
    pre_close = FloatField(null=True)   # 前收盘价
    suspend_flag = IntegerField(null=True) # 停牌标记 (0-正常, 1-停牌)

    class Meta:
        # 联合主键更新为 stock_code + date
        primary_key = CompositeKey('stock_code', 'date')

class DailyBasic(MarketBaseModel):
    """
    股票每日指标数据模型 (基于 Tushare daily_basic 接口)
    """
    # 基础信息
    stock_code = CharField(max_length=20, help_text='TS股票代码')  # 原 ts_code
    date = CharField(help_text='交易日期')         # 原 trade_date (基于图片类型 str，通常为 YYYYMMDD 格式)
    
    # 价格与交易量指标
    close = FloatField(null=True, help_text='当日收盘价')
    turnover_rate = FloatField(null=True, help_text='换手率（%）')
    turnover_rate_f = FloatField(null=True, help_text='换手率（自由流通股）')
    volume_ratio = FloatField(null=True, help_text='量比')
    
    # 估值指标
    pe = FloatField(null=True, help_text='市盈率（总市值/净利润，亏损的PE为空）')
    pe_ttm = FloatField(null=True, help_text='市盈率（TTM，亏损的PE为空）')
    pb = FloatField(null=True, help_text='市净率（总市值/净资产）')
    ps = FloatField(null=True, help_text='市销率')
    ps_ttm = FloatField(null=True, help_text='市销率（TTM）')
    dv_ratio = FloatField(null=True, help_text='股息率（%），除息日发生在去年期间的派现')
    dv_ttm = FloatField(null=True, help_text='股息率（TTM）（%），除息日在近12个月且分红报告期在12个月以内的派现')
    
    # 股本与市值指标
    total_share = FloatField(null=True, help_text='总股本（万股）')
    float_share = FloatField(null=True, help_text='流通股本（万股）')
    free_share = FloatField(null=True, help_text='自由流通股本（万）')
    total_mv = FloatField(null=True, help_text='总市值（万元）')
    circ_mv = FloatField(null=True, help_text='流通市值（万元）')

    class Meta:
        table_name = 'daily_basic' # 你可以根据需要修改表名
        
        # 通常股票代码和日期可以作为联合唯一索引
        primary_key = CompositeKey('stock_code', 'date')

# 确保表存在
market_db.connect()
market_db.create_tables([KlineData, DailyBasic])
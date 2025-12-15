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

# 确保表存在
market_db.connect()
market_db.create_tables([KlineData])
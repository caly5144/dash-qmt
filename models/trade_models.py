from peewee import CharField, FloatField, IntegerField, DateTimeField, AutoField
from datetime import datetime
from . import trade_db, TradeBaseModel

class TradeRecord(TradeBaseModel):
    """成交记录表"""
    id = AutoField()
    # --- 核心唯一标识 ---
    # QMT的成交编号，全局唯一，用于去重
    traded_id = CharField(unique=True, index=True) 
    order_id = CharField(index=True) # 委托编号
    
    # --- 基础信息 ---
    stock_code = CharField()         # 代码 (e.g. 600519.SH)
    stock_name = CharField(null=True)
    trade_time = DateTimeField()     # 成交时间
    trade_date = CharField(index=True)
    
    # --- QMT 原始字段 (保持与文档一致) ---
    # 参考 xtconstant 定义
    order_type = IntegerField()      # 委托类型 (23:买, 24:卖 ...)
    direction = IntegerField(null=True)       # 多空方向 (48:多, 49:空)
    offset_flag = IntegerField(null=True)     # 开平标志 (48:开, 49:平 ...)
    
    # --- 核心数据 ---
    price = FloatField()             # 成交均价
    volume = IntegerField()          # 成交数量 (绝对值，恒为正)
    amount = FloatField()            # 成交金额 (绝对值，恒为正)
    commission = FloatField(default=0.0)   # 佣金
    stamp_duty = FloatField(default=0.0)   # 印花税
    other_fees = FloatField(default=0.0)   # 其他费用(过户费等)
    total_fees = FloatField(default=0.0)   # 总费用
    
    # --- 计算专用字段 ---
    # side: 1 (买入/开仓), -1 (卖出/平仓)
    # 用于计算持仓变化: delta_pos = volume * side
    # 用于计算资金变化: delta_cash = -1 * amount * side - commission
    side = IntegerField() 
    
    # --- 其他 ---
    strategy_name = CharField(default='手动下单')
    source = CharField(default='auto') # auto, manual
    remark = CharField(null=True)

class OrderRecord(TradeBaseModel):
    """委托记录表 (支持状态更新)"""
    id = AutoField()
    
    # --- 核心唯一标识 ---
    # order_id 是全局唯一的，设为唯一索引，用于更新去重
    order_id = CharField(unique=True, index=True) 
    
    # --- 基础信息 ---
    stock_code = CharField()         # 代码
    stock_name = CharField(null=True)
    order_time = DateTimeField()     # 报单时间
    order_date = CharField(index=True)
    
    # --- QMT 原始字段 ---
    order_type = IntegerField()      # 委托类型 (23:买, 24:卖...)
    direction = IntegerField(null=True) # 多空
    offset_flag = IntegerField(null=True) # 开平
    price_type = IntegerField(null=True) # 报价类型
    
    # --- 状态与数量 ---
    order_volume = IntegerField()    # 委托数量
    price = FloatField()             # 委托价格
    traded_volume = IntegerField(default=0) # 已成交数量
    traded_price = FloatField(default=0.0)  # 成交均价
    order_status = IntegerField()    # 委托状态 (50:已报, 56:已成...)
    status_msg = CharField(null=True) # 状态描述
    
    
    # --- 计算字段 ---
    side = IntegerField() # 1:买/开, -1:卖/平
    
    # --- 其他 ---
    strategy_name = CharField(null=True)
    order_remark = CharField(null=True)
    source = CharField(default='auto')

class FundFlow(TradeBaseModel):
    """资金流水表（出入金）"""
    id = AutoField()
    date = DateTimeField(default=datetime.now)
    flow_type = CharField() # 'deposit' (入金) / 'withdraw' (出金)
    amount = FloatField()   # 金额
    remark = CharField(null=True)

class DailyPerformance(TradeBaseModel):
    """每日绩效快照"""
    date = CharField(unique=True) # YYYY-MM-DD
    total_asset = FloatField()    # 总资产
    market_value = FloatField()   # 持仓市值
    cash = FloatField()           # 可用资金
    daily_return = FloatField()   # 当日收益

# 初始化表
trade_db.connect()
trade_db.create_tables([TradeRecord, FundFlow, DailyPerformance, OrderRecord], safe=True)
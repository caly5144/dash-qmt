import time
import pandas as pd
from datetime import datetime
from xtquant import xtdata
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant
from models.trade_models import TradeRecord, OrderRecord
from utils.fee_calculator import FeeCalculator
from utils.stock_info_manager import stock_info_manager
from peewee import IntegrityError
from configs.settings import GLOBAL_SECRETS

class XtManager:
    _instance = None
    
    # 配置
    MINI_QMT_PATH = GLOBAL_SECRETS.get("MINI_QMT_PATH", "")
    ACCOUNT_ID = GLOBAL_SECRETS.get("ACCOUNT_ID", "")
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(XtManager, cls).__new__(cls)
            cls._instance.init_trader()
        return cls._instance

    def init_trader(self):
        if not self.MINI_QMT_PATH or not self.ACCOUNT_ID:
            print("【错误】未配置 QMT 路径或账号，请检查 secrets/config.json")
            self.trader = None
            return
        try:
            session_id = int(time.time())
            self.trader = XtQuantTrader(self.MINI_QMT_PATH, session_id)
            
            # 注册回调
            self.callback = MyTraderCallback()
            self.trader.register_callback(self.callback)
            
            self.trader.start()
            res = self.trader.connect()
            
            if res == 0:
                self.acc = StockAccount(self.ACCOUNT_ID)
                print("MiniQMT 连接成功")
                # 必须订阅才能收到回调和资金推送
                self.trader.subscribe(self.acc)

                # 【新增】应用启动时，检查是否需要更新代码表
                if not stock_info_manager._cache:
                    stock_info_manager.refresh_mapping()

                # 1. 同步成交 (原有)
                print("正在自动同步当日成交...")
                t_count = self.sync_trades()
                
                # 2. 【新增】同步委托
                print("正在自动同步当日委托...")
                o_count = self.sync_orders()
                
                print(f"启动同步完成: 成交+{t_count}, 委托+{o_count}")
            else:
                print(f"MiniQMT 连接失败: {res}")
                self.trader = None
        except Exception as e:
            print(f"初始化交易接口失败: {e}")
            self.trader = None

    def _calc_side(self, order_type, direction, offset_flag):
        """
        根据QMT的原始字段计算交易方向系数 (1 或 -1)
        用于后续计算持仓和资金变化
        """
        # 1. 股票买卖 (Stock)
        if order_type == xtconstant.STOCK_BUY:
            return 1
        elif order_type == xtconstant.STOCK_SELL:
            return -1
            
        # 2. 融资融券 (Credit)
        if order_type in [xtconstant.CREDIT_BUY, xtconstant.CREDIT_FIN_BUY, xtconstant.CREDIT_BUY_SECU_REPAY]:
            return 1
        elif order_type in [xtconstant.CREDIT_SELL, xtconstant.CREDIT_SLO_SELL, xtconstant.CREDIT_SELL_SECU_REPAY]:
            return -1
            
        # 3. 期货 (Future) - 简化逻辑
        # 开多(48,48) -> 1, 平多(49,48) -> -1
        # 开空(48,49) -> -1, 平空(49,49) -> 1 (注意：平空是买入操作，资金流出但持仓变化不同，此处仅定义逻辑方向)
        # 建议：如果只做股票，保留上面部分即可。
        
        # 默认返回 0 (未知)
        return 0

    def sync_trades(self):
        """
        手动同步当日成交 (补充遗漏的推送)
        使用 traded_id 进行去重
        """
        if not self.trader: return 0
        
        # 查询当日所有成交
        trades = self.trader.query_stock_trades(self.acc)
        if not trades: return 0
        
        count = 0
        for t in trades:
            try:
                # 检查 traded_id 是否已存在
                if TradeRecord.select().where(TradeRecord.traded_id == str(t.traded_id)).exists():
                    continue

                # 计算 side
                side = self._calc_side(t.order_type, t.direction, t.offset_flag)
                fees = FeeCalculator.calculate_all_fees(t.stock_code, t.traded_price, t.traded_volume, side)

                if not t.strategy_name:
                    strategy_name = '手动下单'
                else:
                    strategy_name = t.strategy_name
                
                name = stock_info_manager.get_stock_name(t.stock_code)
                # 插入数据库
                dt = datetime.fromtimestamp(t.traded_time)
                TradeRecord.create(
                    traded_id=str(t.traded_id), # 关键：使用成交ID去重
                    order_id=str(t.order_id),
                    stock_code=t.stock_code,
                    stock_name=name,
                    trade_time=dt,
                    trade_date=dt.strftime('%Y-%m-%d'),
                    
                    # 原始字段
                    order_type=t.order_type,
                    direction=t.direction,
                    offset_flag=t.offset_flag,
                    
                    price=t.traded_price,
                    volume=t.traded_volume,
                    amount=t.traded_amount,
                    
                    # 计算字段
                    side=side,
                    
                    strategy_name=strategy_name,
                    source='auto', 
                    remark=t.order_remark,
                    
                    # 【新增】填入计算出的费用
                    commission=fees['commission'],
                    stamp_duty=fees['stamp_duty'],
                    other_fees=fees['other_fees'],
                    total_fees=fees['total_fees']
                )
                count += 1
            except Exception as e:
                print(f"同步单条成交失败: {e}")
                
        # print(f"同步完成，新增 {count} 条记录")
        return count
    
    def sync_orders(self):
        """
        同步当日委托 (使用 replace 逻辑，支持状态更新)
        """
        if not self.trader: return 0
        
        # 查询当日所有委托
        orders = self.trader.query_stock_orders(self.acc, cancelable_only=False)
        if not orders: return 0
        
        count = 0
        for o in orders:
            try:
                # 计算 side
                side = self._calc_side(o.order_type, o.direction, o.offset_flag)

                if not o.strategy_name:
                    strategy_name = '手动下单'
                else:
                    strategy_name = o.strategy_name
                
                name = stock_info_manager.get_stock_name(o.stock_code)
                dt = datetime.fromtimestamp(o.order_time)
                # 使用 replace 插入或更新
                # 这会根据 order_id (唯一索引) 来判断是新增还是覆盖
                OrderRecord.replace(
                    order_id=str(o.order_id),
                    stock_code=o.stock_code,
                    stock_name=name,
                    order_time=dt,
                    order_date=dt.strftime('%Y-%m-%d'),
                    
                    order_type=o.order_type,
                    direction=o.direction,
                    offset_flag=o.offset_flag,
                    price_type=o.price_type,
                    
                    order_volume=o.order_volume,
                    price=o.price,
                    traded_volume=o.traded_volume,
                    traded_price=o.traded_price,
                    order_status=o.order_status,
                    status_msg=o.status_msg,
                    
                    
                    side=side,
                    strategy_name=strategy_name,
                    order_remark=o.order_remark,
                    source='auto'
                ).execute()
                
                count += 1
            except Exception as e:
                print(f"同步单条委托失败: {e}")
                
        return count
    
    def check_connection(self):
        """
        检查连接状态，如果断开则自动重连
        返回: (is_connected, message)
        """
        # 1. 如果对象都没初始化，直接尝试初始化
        if not self.trader:
            print("【监控】XtQuant未初始化，尝试初始化...")
            self.init_trader()
            if self.trader:
                return True, "重新初始化成功"
            else:
                return False, "初始化失败"

        # 2. 尝试连接 (connect是轻量级的，如果已连接会返回0)
        try:
            res = self.trader.connect()
            if res == 0:
                # 连接正常，顺便检查一下账号订阅状态
                return True, "连接正常"
            
            # 3. 连接失败，尝试重连
            print(f"【监控】检测到连接断开(code={res})，尝试重连...")
            # 重新初始化整个实例（有时候句柄失效需要重建）
            self.init_trader()
            
            if self.trader and self.trader.connect() == 0:
                return True, "自动重连成功"
            else:
                return False, "自动重连失败"
                
        except Exception as e:
            print(f"【监控】连接检查异常: {e}")
            return False, f"检测异常: {str(e)}"

    def get_market_data(self, stock_code, period='1d', count=100):
        # ... (保持不变) ...
        df = xtdata.get_market_data_ex(stock_list=[stock_code], period=period, count=count).get(stock_code)
        if df is None or df.empty:
            return pd.DataFrame()
        return df.reset_index()
    
    def subscribe(self, stock_code, period='1d'):
        """
        【新增】订阅指定合约的行情，确保能获取实时数据
        """
        try:
            # 订阅最新行情 (idempotent, 重复调用无副作用)
            # count=0 表示从当前时刻开始订阅增量更新
            xtdata.subscribe_quote(stock_code, period=period, count=0)
            return True
        except Exception as e:
            print(f"订阅失败 {stock_code}: {e}")
            return False

    def get_market_data(self, stock_code, period='1d', count=200): # 默认获取200根
        # 确保数据已下载或有缓存 (自动下载逻辑在 get_market_data_ex 内部有一定支持，但最好显式订阅)
        # 这里直接读取缓存
        data = xtdata.get_market_data_ex(stock_list=[stock_code], period=period, count=count).get(stock_code)
        
        if data is None or data.empty:
            return pd.DataFrame()
        
        # 统一格式化
        df = data.reset_index()
        
        # 兼容处理：确保有 time 列
        if 'time' not in df.columns and 'index' in df.columns:
            df.rename(columns={'index': 'time'}, inplace=True)
            
        return df

# --- 回调类定义 ---
class MyTraderCallback(XtQuantTraderCallback):
    def on_disconnected(self):
        print("【XtQuant】连接断开")

    def on_stock_trade(self, trade):
        """
        实时成交推送
        """
        try:
            print(f"【XtQuant】收到成交推送: {trade.stock_code}")
            
            # 使用 Manager 中的逻辑计算 side
            manager = XtManager() 
            side = manager._calc_side(trade.order_type, trade.direction, trade.offset_flag)
            fees = FeeCalculator.calculate_all_fees(trade.stock_code, trade.traded_price, trade.traded_volume, side)

            if not trade.strategy_name:
                strategy_name = '手动下单'
            else:
                strategy_name = trade.strategy_name

            name = stock_info_manager.get_stock_name(trade.stock_code)
            dt = datetime.fromtimestamp(trade.traded_time)
            
            TradeRecord.create(
                traded_id=str(trade.traded_id), # 唯一键去重
                order_id=str(trade.order_id),
                stock_code=trade.stock_code,
                stock_name=name,
                trade_time=dt,
                trade_date=dt.strftime('%Y-%m-%d'),
                
                # 原始字段
                order_type=trade.order_type,
                direction=trade.direction,
                offset_flag=trade.offset_flag,
                
                price=trade.traded_price,
                volume=trade.traded_volume,
                amount=trade.traded_amount,
                
                side=side,
                
                strategy_name=strategy_name,
                source='auto',
                remark=trade.order_remark,

                commission=fees['commission'],
                stamp_duty=fees['stamp_duty'],
                other_fees=fees['other_fees'],
                total_fees=fees['total_fees']
            )
        except IntegrityError:
            print(f"【XtQuant】忽略重复推送: {trade.traded_id}")
        except Exception as e:
            print(f"【XtQuant】入库失败: {e}")
    
    def on_stock_order(self, order):
        """
        【新增】委托回报推送
        当订单状态变化（如已报、部成、已成、废单）时触发
        """
        try:
            print(f"【XtQuant】收到委托推送: {order.stock_code} 状态:{order.order_status}")
            
            manager = XtManager()
            side = manager._calc_side(order.order_type, order.direction, order.offset_flag)
            
            if not order.strategy_name:
                strategy_name = '手动下单'
            else:
                strategy_name = order.strategy_name
            
            name = stock_info_manager.get_stock_name(order.stock_code)
            dt = datetime.fromtimestamp(order.order_time)
            
            # 同样使用 replace 进行更新或插入
            OrderRecord.replace(
                order_id=str(order.order_id),
                stock_code=order.stock_code,
                stock_name=name,
                order_time=dt,
                order_date=dt.strftime('%Y-%m-%d'),
                
                order_type=order.order_type,
                direction=order.direction,
                offset_flag=order.offset_flag,
                price_type=order.price_type,
                
                order_volume=order.order_volume,
                price=order.price,
                traded_volume=order.traded_volume,
                traded_price=order.traded_price,
                order_status=order.order_status,
                status_msg=order.status_msg,
                
                
                side=side,
                strategy_name=strategy_name,
                order_remark=order.order_remark,
                source='auto'
            ).execute()
            
        except Exception as e:
            print(f"【XtQuant】更新委托记录失败: {e}")

# 全局单例
xt_manager = XtManager()
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
                self.trader.subscribe(self.acc)

                if not stock_info_manager._cache:
                    stock_info_manager.refresh_mapping()

                # 1. 同步成交 (合并模式)
                print("正在自动同步当日成交...")
                t_count = self.sync_trades()
                
                # 2. 同步委托
                print("正在自动同步当日委托...")
                o_count = self.sync_orders()
                
                print(f"启动同步完成: 成交(合并后)+{t_count}, 委托+{o_count}")
            else:
                print(f"MiniQMT 连接失败: {res}")
                self.trader = None
        except Exception as e:
            print(f"初始化交易接口失败: {e}")
            self.trader = None

    def _calc_side(self, order_type, direction, offset_flag):
        """计算交易方向系数"""
        if order_type == xtconstant.STOCK_BUY:
            return 1
        elif order_type == xtconstant.STOCK_SELL:
            return -1
        
        if order_type in [xtconstant.CREDIT_BUY, xtconstant.CREDIT_FIN_BUY, xtconstant.CREDIT_BUY_SECU_REPAY]:
            return 1
        elif order_type in [xtconstant.CREDIT_SELL, xtconstant.CREDIT_SLO_SELL, xtconstant.CREDIT_SELL_SECU_REPAY]:
            return -1
            
        return 0

    def _process_merge_and_save(self, trade_list):
        """
        【核心逻辑】接收原始成交列表，按 order_id 合并后入库
        逻辑：
        1. 按 order_id 分组
        2. 计算总数量、总金额、加权均价
        3. 重新计算总费用
        4. 找出该组最早的 traded_id 作为主ID，删除其余分笔ID，确保数据库只有一条合并记录
        """
        if not trade_list: return 0
        
        # 转 DataFrame 方便处理
        data = []
        for t in trade_list:
            # 【修复】手动提取属性，而不是依赖 __dict__
            if isinstance(t, dict):
                d = t
            else:
                # XtTrade 对象属性提取
                d = {
                    'traded_id': str(t.traded_id),
                    'order_id': str(t.order_id),
                    'stock_code': t.stock_code,
                    'traded_time': t.traded_time,
                    'order_type': t.order_type,
                    'direction': t.direction,
                    'offset_flag': t.offset_flag,
                    'traded_price': t.traded_price,
                    'traded_volume': t.traded_volume,
                    'traded_amount': t.traded_amount,
                    'strategy_name': t.strategy_name,
                    'order_remark': t.order_remark
                }
            data.append(d)
            
        df = pd.DataFrame(data)
        if df.empty: return 0
        
        count = 0
        
        # 按 order_id 分组处理
        for order_id, group in df.groupby('order_id'):
            try:
                # 1. 聚合计算
                total_volume = group['traded_volume'].sum()
                total_amount = group['traded_amount'].sum()
                
                if total_volume == 0: continue
                
                # 加权均价
                avg_price = total_amount / total_volume
                
                # 2. 确定代表信息 (取最早的一笔)
                group = group.sort_values('traded_time') # 按时间正序
                first = group.iloc[0] # 最早一笔
                last = group.iloc[-1] # 最新一笔 (用于更新时间)
                
                # 3. 确定主键 ID (使用第一笔的 traded_id)
                # 这样能保证多次推送时 ID 稳定
                primary_traded_id = first['traded_id']
                
                # 4. 清理旧数据 (关键步骤)
                # 找出该组中除了主ID以外的所有 traded_id，从数据库删除
                # 这样可以把之前的分笔记录清理掉，只留合并后的
                all_ids = group['traded_id'].tolist()
                ids_to_delete = [tid for tid in all_ids if tid != primary_traded_id]
                
                if ids_to_delete:
                    TradeRecord.delete().where(TradeRecord.traded_id.in_(ids_to_delete)).execute()
                
                # 5. 计算费用 (基于总额)
                side = self._calc_side(first['order_type'], first['direction'], first['offset_flag'])
                fees = FeeCalculator.calculate_all_fees(first['stock_code'], avg_price, total_volume, side)
                
                stock_name = stock_info_manager.get_stock_name(first['stock_code'])
                dt = datetime.fromtimestamp(last['traded_time']) # 使用最新成交时间
                
                strategy = first['strategy_name'] if first['strategy_name'] else '手动下单'

                # 6. 更新/插入主记录
                TradeRecord.replace(
                    traded_id=primary_traded_id, # 始终使用第一笔的ID
                    order_id=order_id,
                    stock_code=first['stock_code'],
                    stock_name=stock_name,
                    trade_time=dt,
                    trade_date=dt.strftime('%Y-%m-%d'),
                    
                    order_type=first['order_type'],
                    direction=first['direction'],
                    offset_flag=first['offset_flag'],
                    
                    price=avg_price,          # 加权均价
                    volume=int(total_volume), # 总量
                    amount=total_amount,      # 总额
                    
                    side=side,
                    strategy_name=strategy,
                    source='auto',
                    remark=first['order_remark'],
                    
                    commission=fees['commission'],
                    stamp_duty=fees['stamp_duty'],
                    other_fees=fees['other_fees'],
                    total_fees=fees['total_fees']
                ).execute()
                
                count += 1
            except Exception as e:
                print(f"合并入库失败 OrderID={order_id}: {e}")
                
        return count

    def sync_trades(self):
        """
        同步当日成交 (自动合并分笔)
        """
        if not self.trader: return 0
        
        # 查询当日所有成交
        trades = self.trader.query_stock_trades(self.acc)
        if not trades: return 0
        
        # 统一交给合并逻辑处理
        return self._process_merge_and_save(trades)
    
    def sync_orders(self):
        """
        同步当日委托 (保持原样，OrderRecord 本身就是聚合状态)
        """
        if not self.trader: return 0
        
        orders = self.trader.query_stock_orders(self.acc, cancelable_only=False)
        if not orders: return 0
        
        count = 0
        for o in orders:
            try:
                side = self._calc_side(o.order_type, o.direction, o.offset_flag)
                strategy_name = o.strategy_name if o.strategy_name else '手动下单'
                name = stock_info_manager.get_stock_name(o.stock_code)
                dt = datetime.fromtimestamp(o.order_time)
                
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
        if not self.trader:
            self.init_trader()
            return (True, "重新初始化成功") if self.trader else (False, "初始化失败")

        try:
            if self.trader.connect() == 0:
                return True, "连接正常"
            self.init_trader()
            return (True, "自动重连成功") if self.trader and self.trader.connect() == 0 else (False, "自动重连失败")
        except Exception as e:
            return False, f"检测异常: {str(e)}"

    def get_market_data(self, stock_code, period='1d', count=200):
        data = xtdata.get_market_data_ex(stock_list=[stock_code], period=period, count=count).get(stock_code)
        if data is None or data.empty: return pd.DataFrame()
        df = data.reset_index()
        if 'time' not in df.columns and 'index' in df.columns:
            df.rename(columns={'index': 'time'}, inplace=True)
        return df
    
    def subscribe(self, stock_code, period='1d'):
        try:
            xtdata.subscribe_quote(stock_code, period=period, count=0)
            return True
        except Exception as e:
            print(f"订阅失败 {stock_code}: {e}")
            return False

# --- 回调类定义 ---
class MyTraderCallback(XtQuantTraderCallback):
    def on_disconnected(self):
        print("【XtQuant】连接断开")

    def on_stock_trade(self, trade):
        """
        实时成交推送 (修改为合并逻辑)
        """
        try:
            print(f"【XtQuant】收到成交推送: {trade.stock_code} ({trade.traded_volume}股)")
            
            # 1. 获取管理器实例
            manager = XtManager()
            if not manager.trader: return

            # 2. 关键：不只是处理这一笔，而是获取该 OrderID 对应的所有成交记录
            # 这样才能保证拿到完整的历史分笔，从而正确计算总数和均价
            all_trades = manager.trader.query_stock_trades(manager.acc)
            
            if all_trades:
                # 3. 过滤出当前委托的所有成交 (Python端过滤，QMT API不支持按Order查询)
                target_order_id = trade.order_id
                related_trades = [t for t in all_trades if t.order_id == target_order_id]
                
                # 4. 如果查询结果里还没包含当前这笔推送(极少数情况)，手动加上
                known_ids = set(t.traded_id for t in related_trades)
                if trade.traded_id not in known_ids:
                    related_trades.append(trade)
                
                # 5. 调用合并处理逻辑
                manager._process_merge_and_save(related_trades)
            
        except Exception as e:
            print(f"【XtQuant】处理成交推送失败: {e}")
    
    def on_stock_order(self, order):
        """
        委托回报推送 (逻辑不变，直接更新)
        """
        try:
            # print(f"【XtQuant】收到委托推送: {order.stock_code} 状态:{order.order_status}")
            manager = XtManager()
            side = manager._calc_side(order.order_type, order.direction, order.offset_flag)
            strategy_name = order.strategy_name if order.strategy_name else '手动下单'
            name = stock_info_manager.get_stock_name(order.stock_code)
            dt = datetime.fromtimestamp(order.order_time)
            
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
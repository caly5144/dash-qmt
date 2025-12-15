import dash
from dash.dependencies import Input, Output, State
from dash import set_props
import feffery_antd_components as fac
from server import app
from models.trade_models import TradeRecord, OrderRecord
from utils.xt_manager import xt_manager
import pandas as pd
from datetime import datetime, date

# --- 辅助函数：格式化方向标签 ---
def _format_direction(row):
    side = row.get('side')
    order_type = row.get('order_type')
    
    label = '未知'
    color = 'default'
    
    if side == 1 or order_type == 23:
        label = '买入'
        color = 'red'
    elif side == -1 or order_type == 24:
        label = '卖出'
        color = 'green'
    
    return {'tag': label, 'color': color}

# --- 辅助函数：格式化状态标签 (委托专用) ---
def _format_status(status_code):
    # 参考 QMT 文档
    mapping = {
        48: {'tag': '未报', 'color': 'default'},
        49: {'tag': '待报', 'color': 'default'},
        50: {'tag': '已报', 'color': 'processing'}, # 蓝色
        51: {'tag': '已报待撤', 'color': 'warning'},
        52: {'tag': '部成待撤', 'color': 'warning'},
        53: {'tag': '部撤', 'color': 'default'},
        54: {'tag': '已撤', 'color': 'default'},
        55: {'tag': '部成', 'color': 'geekblue'},
        56: {'tag': '已成', 'color': 'success'}, # 绿色
        57: {'tag': '废单', 'color': 'error'},
        255: {'tag': '未知', 'color': 'default'}
    }
    return mapping.get(status_code, {'tag': str(status_code), 'color': 'default'})

# --- 核心逻辑：获取数据 ---
def get_trades(is_today=True):
    """获取成交记录 (今日/历史)"""
    today_str = date.today().strftime('%Y-%m-%d')
    
    
    if is_today:
        query = TradeRecord.select().where(TradeRecord.trade_date == today_str).order_by(-TradeRecord.trade_time)
    else:
        # SQLite 字符串比较：小于今天的日期
        query = TradeRecord.select().where(TradeRecord.trade_date < today_str).order_by(-TradeRecord.trade_time)
        
    trades = list(query.dicts())
    df = pd.DataFrame(trades)
    
    if df.empty: return []

    # 格式化字段
    df['trade_time'] = df['trade_time'].astype(str)
    df['direction_label'] = df.apply(_format_direction, axis=1)
    
    # 来源标签
    def format_source(src):
        colors = {'auto': 'blue', 'sync': 'cyan', 'excel': 'orange', 'manual': 'purple'}
        return {'tag': src or 'unknown', 'color': colors.get(src, 'default')}
    df['source'] = df['source'].apply(format_source)

    return df.to_dict('records')

def get_orders(is_today=True):
    """获取委托记录 (今日/历史)"""
    today_str = date.today().strftime('%Y-%m-%d')
    
    # 【优化】同上
    if is_today:
        query = OrderRecord.select().where(OrderRecord.order_date == today_str).order_by(-OrderRecord.order_time)
    else:
        query = OrderRecord.select().where(OrderRecord.order_date < today_str).order_by(-OrderRecord.order_time)
        
    orders = list(query.dicts())
    df = pd.DataFrame(orders)
    
    if df.empty: return []

    # 格式化
    df['order_time'] = df['order_time'].astype(str)
    df['direction_label'] = df.apply(_format_direction, axis=1)
    df['status_label'] = df['order_status'].apply(_format_status)

    return df.to_dict('records')


# --- 回调：统一处理标签页切换和数据刷新 ---
@app.callback(
    [Output('table-today-trade', 'data'),
     Output('table-today-order', 'data'),
     Output('table-hist-trade', 'data'),
     Output('table-hist-order', 'data')],
    [
        Input('trade-init-trigger', 'timeoutCount'), # 页面加载
        Input('trade-manage-tabs', 'activeKey'),     # 切换标签
    ],
    prevent_initial_call=True
)
def update_trade_views(init, active_key):
    res = [dash.no_update] * 4 
    
    update_today_trade = False
    update_today_order = False
    update_hist_trade = False
    update_hist_order = False

    # 默认逻辑
    if not active_key or active_key == 'tab-today-trade': 
        update_today_trade = True
    elif active_key == 'tab-today-order': 
        update_today_order = True
    elif active_key == 'tab-hist-trade': 
        update_hist_trade = True
    elif active_key == 'tab-hist-order': 
        update_hist_order = True

    if update_today_trade: res[0] = get_trades(is_today=True)
    if update_today_order: res[1] = get_orders(is_today=True)
    if update_hist_trade:  res[2] = get_trades(is_today=False)
    if update_hist_order:  res[3] = get_orders(is_today=False)

    return res
import dash
from dash.dependencies import Input, Output, State
from dash import set_props
import feffery_antd_components as fac
from server import app
from models.trade_models import TradeRecord, OrderRecord, FundFlow, trade_db
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

def get_fund_flow():
    """获取资金流水"""
    # 查询所有流水并按日期降序排列
    query = FundFlow.select().order_by(FundFlow.date.desc())
    
    data = []
    for item in query:
        data.append({
            'key': str(item.id),
            'date': item.date.strftime('%Y-%m-%d'),
            'type': '入金' if item.flow_type == 'deposit' else '出金',
            'amount': f"{item.amount:,.2f}",
            'remark': item.remark
        })
        
    return data


# --- 回调：统一处理标签页切换和数据刷新 ---
@app.callback(
    [Output('table-today-trade', 'data'),
     Output('table-today-order', 'data'),
     Output('table-hist-trade', 'data'),
     Output('table-hist-order', 'data'),
     Output('trade-fund-flow-table', 'data')],
    [
        Input('trade-init-trigger', 'timeoutCount'), # 页面加载
        Input('trade-manage-tabs', 'activeKey'),     # 切换标签
    ],
    prevent_initial_call=True
)
def update_trade_views(init, active_key):
    res = [dash.no_update] * 5 
    
    update_today_trade = False
    update_today_order = False
    update_hist_trade = False
    update_hist_order = False
    update_fund_flow = False

    # 默认逻辑
    if not active_key or active_key == 'tab-today-trade': 
        update_today_trade = True
    elif active_key == 'tab-today-order': 
        update_today_order = True
    elif active_key == 'tab-hist-trade': 
        update_hist_trade = True
    elif active_key == 'tab-hist-order': 
        update_hist_order = True
    elif active_key == 'history-flow': 
        update_fund_flow = True

    if update_today_trade: res[0] = get_trades(is_today=True)
    if update_today_order: res[1] = get_orders(is_today=True)
    if update_hist_trade:  res[2] = get_trades(is_today=False)
    if update_hist_order:  res[3] = get_orders(is_today=False)
    if update_fund_flow:  res[4] = get_fund_flow()

    return res


# --- 回调 2: 点击“新增”按钮打开模态框 ---
@app.callback(
    Output('add-fund-flow-modal', 'visible'),
    Input('add-fund-flow-btn', 'nClicks'),
    prevent_initial_call=True
)
def open_flow_modal(n):
    return True


# --- 回调 3: 确认提交并刷新表格 ---
# 巧妙避开 allow_duplicate：Output 指向确定按钮的 loading 状态
@app.callback(
    Output('add-fund-flow-modal', 'confirmLoading'), 
    Input('add-fund-flow-modal', 'okCounts'),
    [State('add-flow-date', 'value'),
     State('add-flow-type', 'value'),
     State('add-flow-amount', 'value'),
     State('add-flow-remark', 'value')],
    prevent_initial_call=True
)
def handle_add_fund_flow(ok, date_val, type_val, amount_val, remark_val):
    if not ok:
        return False
    if not all([date_val, type_val, amount_val]):
        set_props('global-message', {
            'children': fac.AntdMessage(content='请填写完整日期、类型和金额！', type='error')
        })
        return False # 关闭按钮的 loading 状态

    try:
        # 处理备注中的 nan 问题
        final_remark = remark_val if remark_val and str(remark_val).lower() != 'nan' else None

        # 写入数据库
        with trade_db.connection_context():
            FundFlow.create(
                date=datetime.strptime(date_val, '%Y-%m-%d'),
                flow_type=type_val,
                amount=float(amount_val),
                remark=final_remark
            )
        
        # 提示成功
        set_props('global-message', {
            'children': fac.AntdMessage(content='资金流水保存成功！', type='success')
        })

        # 重新查询最新数据以刷新表格
        with trade_db.connection_context():
            query = FundFlow.select().order_by(FundFlow.date.desc())
            new_data = [
                {
                    'key': str(item.id),
                    'date': item.date.strftime('%Y-%m-%d'),
                    'type': '入金' if item.flow_type == 'deposit' else '出金',
                    'amount': f"{item.amount:,.2f}",
                    'remark': item.remark or '-'
                } for item in query
            ]
        
        # 【核心技巧】使用 set_props 跨组件静默更新，不走 Output，彻底解决冲突报错
        set_props('trade-fund-flow-table', {'data': new_data})
        set_props('add-fund-flow-modal', {'visible': False})
        
        # 可选优化：清空表单，方便下次录入
        set_props('add-flow-date', {'value': None})
        set_props('add-flow-type', {'value': None})
        set_props('add-flow-amount', {'value': None})
        set_props('add-flow-remark', {'value': None})

        return False # 关闭按钮的 loading 状态
        
    except Exception as e:
        set_props('global-message', {
            'children': fac.AntdMessage(content=f'保存失败: {str(e)}', type='error')
        })
        return False # 关闭按钮的 loading 状态
    
@app.callback(
    Output('delete-fund-flow-confirm', 'id'), # 占位 Output，实际用 set_props
    Input('delete-fund-flow-confirm', 'confirmCounts'),
    State('trade-fund-flow-table', 'selectedRowKeys'),
    prevent_initial_call=True
)
def handle_delete_fund_flow(confirm_counts, selected_keys):
    if not confirm_counts:
        return dash.no_update
        
    # 如果没有勾选任何行
    if not selected_keys:
        set_props('global-message', {
            'children': fac.AntdMessage(content='请先在表格中勾选要删除的记录！', type='warning')
        })
        return dash.no_update
        
    try:
        with trade_db.connection_context():
            # 在数据库中批量删除勾选的 id
            FundFlow.delete().where(FundFlow.id.in_(selected_keys)).execute()
            
            # 重新查询最新数据刷新表格
            query = FundFlow.select().order_by(FundFlow.date.desc())
            new_data = [
                {
                    'key': str(item.id),
                    'date': item.date.strftime('%Y-%m-%d'),
                    'type': '入金' if item.flow_type == 'deposit' else '出金',
                    'amount': f"{item.amount:,.2f}",
                    'remark': item.remark or '-'
                } for item in query
            ]
            
        set_props('global-message', {
            'children': fac.AntdMessage(content=f'成功删除 {len(selected_keys)} 条流水记录！', type='success')
        })
        
        # 刷新表格数据，并且清空勾选状态（selectedRowKeys 置空）
        set_props('trade-fund-flow-table', {
            'data': new_data,
            'selectedRowKeys': [] 
        })
        
    except Exception as e:
        set_props('global-message', {
            'children': fac.AntdMessage(content=f'删除失败: {str(e)}', type='error')
        })
        
    return dash.no_update
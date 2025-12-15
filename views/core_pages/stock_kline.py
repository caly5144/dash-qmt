import dash
import pandas as pd
from yarl import URL
from dash import dcc, html
import feffery_antd_components as fac
import feffery_utils_components as fuc
from dash.dependencies import Input, Output, State, ClientsideFunction
from server import app
from models.market_models import KlineData  # 引用之前建立的模型


def get_kline_data_from_db(stock_code):
    try:
        # 查询数据库
        query = KlineData.select().where(
            (KlineData.stock_code == stock_code) & 
            (KlineData.date >= '2022-01-01')
        ).order_by(KlineData.date)
        
        df = pd.DataFrame(list(query.dicts()))
        
        if df.empty:
            return {'code': 204, 'msg': 'data not found', 'data': []}

        # 数据清洗适配
        df['timestamp'] = (pd.to_datetime(df['date']) - pd.Timedelta(hours=8)).view("i8") // 10 ** 6
        df = df.rename(columns={'amount': 'turnover'})
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']
        for col in required_cols:
            if col not in df.columns: df[col] = 0
    
        # print(df)
        return {
            'code': 200,
            'msg': 'success',
            'data': {'contract': stock_code, 'df': df[required_cols].to_dict('records')}
        }
    except Exception as e:
        return {'code': 500, 'msg': str(e), 'data': []}

# 设置模态框
stock_line_SETTING_MODAL = fac.AntdModal(
    id='stock-line_modal_setting',
    title='图表设置',
    width=500,
    children=[
        html.Div(fac.AntdSpace([
            fac.AntdFormItem(fac.AntdSelect(
                id='stock-line_modal_candle_type',
                options=[
                    {"label": "全实心", "value": "candle_solid"},
                    {"label": "全空心", "value": "candle_stroke"},
                    {"label": "涨空心", "value": "candle_up_stroke"},
                    {"label": "跌空心", "value": "candle_down_stroke"},
                ],
                value='candle_solid', persistence=True
            ), label='蜡烛图类型', colon=False),
            fac.AntdFormItem(fac.AntdSwitch(id='stock-line_modal_grid', checked=True, persistence=True), 
                           label='网格线', colon=False),
        ], size=20, wrap=True))
    ]
)

# 页面渲染入口
def render():
    
    return html.Div(
        [
            # 数据存储
            dcc.Store(id='stock-line_store', storage_type='session'),
            # 消息提示
            html.Div(id='stock-line_message_container'),
            # 设置弹窗
            stock_line_SETTING_MODAL,
            
            # 顶部操作栏
            html.Div(
                fac.AntdSpace([
                    fac.AntdInput(
                        id='stock-line_input_contract',
                        addonBefore='证券代码',
                        placeholder='例如: 000001.SZ',
                        style={'width': '300px'},
                    ),
                    fac.AntdButton(
                        '查询', id='stock-line_search', type='primary',
                        icon=fac.AntdIcon(icon='antd-search')
                    ),
                    fac.AntdButton(
                        '设置', id='stock-line_setting_btn',
                        icon=fac.AntdIcon(icon='antd-setting')
                    ),
                ]),
                style={'background': 'white', 'borderRadius': '8px', 'marginBottom': '12px'}
            ),
            
            # 图表容器
            html.Div(
                html.Div(id='stock-line_kline_container', style={'height': '100%'}),
                style={'height': '90%', 'background': 'white', 'borderRadius': '8px', 'padding': '16px'}
            ),
        ],
        style={'height': '97vh'}
    )

# --- Callbacks ---

# 1. 自动从URL读取参数并查询
@app.callback(
    [Output('stock-line_input_contract', 'value'),
     Output('stock-line_search', 'nClicks')],
    Input('core-url', 'href')
)
def auto_search_from_url(current_url):

    parsed_url = URL(current_url)
    if 'code' in parsed_url.query:
        code = parsed_url.query.get('code')
        return code, 1 # 自动填充并触发查询点击
    else:
        return dash.no_update
    

# 2. 执行数据查询
@app.callback(
    Output('stock-line_store', 'data'),
    Input('stock-line_search', 'nClicks'),
    State('stock-line_input_contract', 'value'),
    prevent_initial_call=True
)
def execute_query(n_clicks, contract):
    if not contract: return dash.no_update
    return get_kline_data_from_db(contract)

# 3. 客户端渲染图表 (复用 assets/js/kline_render.js 中的逻辑)
app.clientside_callback(
    ClientsideFunction(namespace="kline", function_name="renderChart"),
    Output("stock-line_kline_container", "children"),
    Input("stock-line_store", "data"),
    [
        State("stock-line_kline_container", "id"),
        State("stock-line_search", "nClicks"),
        State("stock-line_modal_candle_type", "value"),
        # 下面这些参数需要与JS函数签名匹配，这里简化传参
        State("stock-line_modal_candle_type", "value"), # 占位: last_price
        State("stock-line_modal_candle_type", "value"), # 占位: high_price
        State("stock-line_modal_candle_type", "value"), # 占位: low_price
        State("stock-line_modal_candle_type", "value"), # 占位: last_value
        State("stock-line_modal_candle_type", "value"), # 占位: axis_type
        State("stock-line_modal_candle_type", "value"), # 占位: reverse
        State("stock-line_modal_grid", "checked"),
    ],
    prevent_initial_call=True
)

# 4. 弹窗控制
app.clientside_callback(
    """function(n) { return n > 0; }""",
    Output('stock-line_modal_setting', 'visible'),
    Input('stock-line_setting_btn', 'nClicks'),
    prevent_initial_call=True
)
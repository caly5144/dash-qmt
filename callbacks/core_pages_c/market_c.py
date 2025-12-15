from dash.dependencies import Input, Output
import plotly.graph_objects as go
from server import app
from utils.xt_manager import xt_manager
from dash import dcc

@app.callback(
    Output('market-kline-container', 'children'),
    [Input('market-stock-select', 'value'),
     Input('market-period-select', 'value')]
)
def update_kline(stock_code, period):
    if not stock_code: return None
    
    # 从 XtQuant 获取数据
    df = xt_manager.get_market_data(stock_code, period=period)
    
    if df.empty:
        return dcc.Graph()

    # 使用 Plotly 绘制 K 线
    fig = go.Figure(data=[go.Candlestick(
        x=df['time'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close']
    )])
    
    fig.update_layout(
        title=f'{stock_code} {period} K线',
        xaxis_rangeslider_visible=False,
        margin=dict(l=20, r=20, t=40, b=20),
        height=500
    )
    
    return dcc.Graph(figure=fig)
from dash.dependencies import Input, Output, State
from dash import set_props, dash, callback
import feffery_antd_components as fac
from server import app
from utils.xt_manager import xt_manager
from utils.stock_info_manager import stock_info_manager

# --- 回调1: 定时检查 QMT 连接状态 ---
@app.callback(
    [Output("core-qmt-status-badge", "count"),
     Output("core-qmt-status-popover", "content")],
    Input("core-qmt-check-interval", "n_intervals")
)
def check_qmt_status(n):
    # 执行检查（内部会自动重连）
    is_connected, msg = xt_manager.check_connection()
    
    if is_connected:
        # 连接正常：清除红点，提示正常
        return 0, f"当前状态：{msg}"
    else:
        # 连接失败：显示红点，更新提示文字
        return 1, f"警告：{msg}，系统正在尝试自动重连..."

# --- 回调2: 打开设置模态框 ---
@app.callback(
    Output("core-setting-modal", "visible"),
    Input("core-setting-btn", "nClicks"),
    prevent_initial_call=True
)
def open_setting_modal(n):
    return True

# --- 回调3: 手动重连 ---
@app.callback(
    Output("core-manual-reconnect-btn", "loading"), # 控制按钮loading状态
    Input("core-manual-reconnect-btn", "nClicks"),
    prevent_initial_call=True
)
def manual_reconnect(n):
    # 强制重新初始化
    xt_manager.init_trader()
    
    # 再次检查
    is_connected, msg = xt_manager.check_connection()
    
    if is_connected:
        set_props("global-message", {
            "children": fac.AntdMessage(content="手动连接成功！", type="success")
        })
    else:
        set_props("global-message", {
            "children": fac.AntdMessage(content=f"连接失败: {msg}", type="error")
        })
        
    return False # 关闭loading

@app.callback(
    Output("core-update-stock-list-btn", "loading"),
    Input("core-update-stock-list-btn", "nClicks"),
    prevent_initial_call=True
)
def update_stock_list_manually(n):
    try:
        count = stock_info_manager.refresh_mapping()
        set_props("global-message", {
            "children": fac.AntdMessage(content=f"更新完成，共收录 {count} 个证券品种", type="success")
        })
    except Exception as e:
        set_props("global-message", {
            "children": fac.AntdMessage(content=f"更新失败: {str(e)}", type="error")
        })
        
    return False
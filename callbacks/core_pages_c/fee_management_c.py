import dash
from dash.dependencies import Input, Output, State
from dash import set_props
import feffery_antd_components as fac
from server import app
from configs.fee_config import fee_manager

# 字段映射字典，用于前端友好显示
FEE_TYPE_MAP = {
    "commission": "佣金",
    "stamp_duty": "印花税",
    "other_fees": "其他费用"
}

MODE_MAP = {
    "both": {"tag": "双边", "color": "blue"},
    "buy": {"tag": "买入", "color": "red"},
    "sell": {"tag": "卖出", "color": "green"},
    "none": {"tag": "不收", "color": "default"}
}

def get_flattened_fees():
    """读取配置并将嵌套字典转换为扁平列表，供表格展示"""
    config = fee_manager.get_config()
    data = []
    
    # 遍历: 市场 -> 品种 -> 费用类型
    for market, products in config.items():
        for product, fees in products.items():
            for fee_type, details in fees.items():
                data.append({
                    # 生成唯一key，便于React渲染
                    'key': f"{market}_{product}_{fee_type}", 
                    'market': market,
                    'product': product,
                    'fee_type': fee_type, # 原始key，用于回填
                    'fee_type_label': FEE_TYPE_MAP.get(fee_type, fee_type), # 显示名称
                    'rate': details.get('rate'),
                    'min_fee': details.get('min_fee'),
                    'mode': details.get('mode'), # 原始值
                    'mode_label': MODE_MAP.get(details.get('mode'), {'tag': '未知', 'color': 'default'}), # 标签样式
                    'operation': {'content': '编辑', 'type': 'link'} # 操作列按钮
                })
    return data

# --- 回调1: 刷新表格 & 保存修改 ---
@app.callback(
    Output('fee-config-table', 'data'),
    [
        # 1. 监听 URL 变化 (页面进入时自动加载)
        Input('core-url', 'pathname'),
        # 2. 监听 弹窗确认 (保存后自动刷新)
        Input('fee-edit-modal', 'okCounts')
        # 【修改】删除了按钮点击的 Input
    ],
    [
        State('fee-edit-form', 'values'),
        State('fee-edit-target-store', 'data')
    ]
    
    # prevent_initial_call=True
)
def refresh_fee_table(pathname, ok_count, form_values, target_context):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # 1. 页面进入逻辑
    # 只有当触发源是 URL 且路径不对时，才跳过更新
    # 这样确保了每次点击菜单进入该页面，都会重新读取最新的 json 配置
    
    if pathname != '/quant/fees':
        return dash.no_update

    # 2. 保存修改逻辑
    if trigger_id == 'fee-edit-modal':
        if form_values and target_context:
            # 【修改】从 Store 中获取定位 Key，而不是从表单获取
            market = target_context.get('market')
            product = target_context.get('product')
            fee_type = target_context.get('fee_type')
            
            if market and product and fee_type:
                current_config = fee_manager.get_config()
                # 检查键是否存在，防止报错
                if market in current_config and product in current_config[market]:
                    target = current_config[market][product][fee_type]
                    # 更新值
                    target['rate'] = form_values.get('edit-rate', 0)
                    target['min_fee'] = form_values.get('edit-min-fee', 0)
                    target['mode'] = form_values.get('edit-mode', 'none')
                    
                    # 写入文件
                    fee_manager.update_config(current_config)
                    
                    # 提示用户
                    set_props("global-message", {
                        "children": fac.AntdMessage(content="费率配置已更新", type="success")
                    })

    # 3. 最终返回：重新读取文件并刷新表格
    return get_flattened_fees()

# --- 回调2: 点击编辑按钮 (保持不变) ---
@app.callback(
    [Output('fee-edit-modal', 'visible'),
     Output('fee-edit-form', 'values'),
     Output('fee-edit-target-store', 'data')], 
    Input('fee-config-table', 'nClicksButton'),
    [State('fee-config-table', 'clickedContent'),
     State('fee-config-table', 'recentlyButtonClickedRow')],
    prevent_initial_call=True
)
def open_edit_modal(nClicks, content, row):
    if content == '编辑' and row:
        # 1. 表单回填数据 (只填可见的)
        form_values = {
            'edit-rate': row['rate'],
            'edit-min-fee': row['min_fee'],
            'edit-mode': row['mode']
        }
        
        # 2. 上下文数据 (存入 Store)
        context_data = {
            'market': row['market'],
            'product': row['product'],
            'fee_type': row['fee_type']
        }
        
        return True, form_values, context_data
    return dash.no_update
import feffery_antd_components as fac
import feffery_utils_components as fuc
from feffery_dash_utils.style_utils import style

def render():
    # 1. 成交类表格列
    cols_trade = [
        {'title': '时间', 'dataIndex': 'trade_time', 'width': 180},
        {'title': '代码', 'dataIndex': 'stock_code', 'width': 120},
        {'title': '名称', 'dataIndex': 'stock_name', 'width': 120}, # 新增名称
        {'title': '方向', 'dataIndex': 'direction_label', 'renderOptions': {'renderType': 'tags'}, 'width': 100},
        {'title': '价格', 'dataIndex': 'price', 'width': 100},
        {'title': '数量', 'dataIndex': 'volume', 'width': 100},
        {'title': '金额', 'dataIndex': 'amount', 'width': 120},
        {'title': '总费用', 'dataIndex': 'total_fees', 'width': 100},
        {'title': '策略', 'dataIndex': 'strategy_name', 'width': 150},
        {'title': '来源', 'dataIndex': 'source', 'renderOptions': {'renderType': 'tags'}, 'width': 100},
    ]

    # 2. 委托类表格列
    cols_order = [
        {'title': '报单时间', 'dataIndex': 'order_time', 'width': 180},
        {'title': '代码', 'dataIndex': 'stock_code', 'width': 120},
        {'title': '名称', 'dataIndex': 'stock_name', 'width': 120},
        {'title': '方向', 'dataIndex': 'direction_label', 'renderOptions': {'renderType': 'tags'}, 'width': 100},
        {'title': '价格', 'dataIndex': 'price', 'width': 100},
        {'title': '委托数量', 'dataIndex': 'order_volume', 'width': 100},
        {'title': '成交数量', 'dataIndex': 'traded_volume', 'width': 100},
        {'title': '状态', 'dataIndex': 'status_label', 'renderOptions': {'renderType': 'tags'}, 'width': 100}, # 状态标签
        {'title': '状态信息', 'dataIndex': 'status_msg', 'width': 150, 'ellipsis': True},
        {'title': '策略', 'dataIndex': 'strategy_name', 'width': 150},
        {'title': '备注', 'dataIndex': 'order_remark', 'width': 150, 'ellipsis': True},
    ]
    return fac.AntdSpace(
        [
            fac.AntdBreadcrumb(items=[{"title": "量化平台"}, {"title": "交易管理"}]),
            fuc.FefferyTimeout(id='trade-init-trigger', delay=0),
            
            # 操作栏
            fac.AntdRow(
                [
                    fac.AntdCol(
                        fac.AntdSpace([
                            fac.AntdButton("出入金记录", id='btn-fund-flow'),
                        ]),
                        span=24
                    )
                ]
            ),

            fac.AntdTabs(
                id='trade-manage-tabs',
                type='card',
                defaultActiveKey='tab-today-trade', # 默认选中当日成交
                items=[
                    {
                        'key': 'tab-today-trade',
                        'label': '当日成交',
                        'children': fac.AntdTable(
                            id='table-today-trade',
                            columns=cols_trade,
                            data=[], 
                            bordered=True,
                            pagination={'pageSize': 10},
                            size='small',
                        )
                    },
                    {
                        'key': 'tab-today-order',
                        'label': '当日委托',
                        'children': fac.AntdTable(
                            id='table-today-order',
                            columns=cols_order,
                            data=[], 
                            bordered=True,
                            pagination={'pageSize': 10},
                            size='small',
                        )
                    },
                    {
                        'key': 'tab-hist-trade',
                        'label': '历史成交',
                        'children': fac.AntdTable(
                            id='table-hist-trade',
                            columns=cols_trade,
                            data=[], 
                            bordered=True,
                            pagination={'pageSize': 20}, # 历史数据多，每页多显示点
                            size='small',
                        )
                    },
                    {
                        'key': 'tab-hist-order',
                        'label': '历史委托',
                        'children': fac.AntdTable(
                            id='table-hist-order',
                            columns=cols_order,
                            data=[], 
                            bordered=True,
                            pagination={'pageSize': 20},
                            size='small',
                        )
                    },
                ]
            )

        ],
        direction="vertical",
        style=style(width="100%"),
    )
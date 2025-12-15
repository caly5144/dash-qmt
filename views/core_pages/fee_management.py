from dash import dcc

import feffery_antd_components as fac
from feffery_dash_utils.style_utils import style


def render():
    return fac.AntdSpace(
        [
            dcc.Store(id='fee-edit-target-store'),
            fac.AntdBreadcrumb(items=[{"title": "量化平台"}, {"title": "费率管理"}]),
            

            # 费率展示表格
            fac.AntdTable(
                id='fee-config-table',
                columns=[
                    {'title': '市场', 'dataIndex': 'market', 'width': 80},
                    {'title': '品种', 'dataIndex': 'product', 'width': 80},
                    {'title': '费用类型', 'dataIndex': 'fee_type_label', 'width': 120},
                    {'title': '费率', 'dataIndex': 'rate', 'width': 120},
                    {'title': '最低收费', 'dataIndex': 'min_fee', 'width': 100},
                    {
                        'title': '收取方式', 
                        'dataIndex': 'mode_label', 
                        'width': 100, 
                        'renderOptions': {'renderType': 'tags'}
                    },
                    {
                        'title': '操作', 
                        'dataIndex': 'operation', 
                        'width': 80, 
                        'renderOptions': {'renderType': 'button'}
                    },
                ],
                data=[], # 初始为空
                bordered=True,
                pagination=False,
                size='small'
            ),

            # 编辑费率弹窗 (保持不变)
            fac.AntdModal(
                id='fee-edit-modal',
                title='修改费率配置',
                renderFooter=True,
                children=[
                    fac.AntdForm(
                        id='fee-edit-form',
                        layout='vertical',
                        enableBatchControl=True,
                        children=[
                            
                            fac.AntdFormItem(
                                fac.AntdInputNumber(
                                    id='edit-rate', 
                                    precision=6, 
                                    step=0.00001, 
                                    style={'width': '100%'}
                                ), 
                                label='费率 (例如: 万2.5 填 0.00025)'
                            ),
                            fac.AntdFormItem(
                                fac.AntdInputNumber(
                                    id='edit-min-fee', 
                                    precision=2, 
                                    step=1, 
                                    style={'width': '100%'}
                                ), 
                                label='最低收费 (元)'
                            ),
                            fac.AntdFormItem(
                                fac.AntdSelect(
                                    id='edit-mode',
                                    options=[
                                        {'label': '双边收取', 'value': 'both'},
                                        {'label': '仅买入收', 'value': 'buy'},
                                        {'label': '仅卖出收', 'value': 'sell'},
                                        {'label': '不收取', 'value': 'none'},
                                    ],
                                    allowClear=False
                                ), 
                                label='收取方式'
                            ),
                        ]
                    )
                ]
            )
        ],
        direction="vertical",
        style=style(width="100%"),
    )
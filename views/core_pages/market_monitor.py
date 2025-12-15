import feffery_antd_components as fac
import feffery_utils_components as fuc
from feffery_dash_utils.style_utils import style

def render():
    return fac.AntdSpace(
        [
            fac.AntdBreadcrumb(items=[{"title": "量化平台"}, {"title": "行情监控"}]),
            fac.AntdRow(
                [
                    fac.AntdCol(
                        fac.AntdSelect(
                            id='market-stock-select',
                            placeholder='请输入代码搜索',
                            options=[
                                {'label': '贵州茅台 (600519.SH)', 'value': '600519.SH'},
                                {'label': '宁德时代 (300750.SZ)', 'value': '300750.SZ'},
                                {'label': '平安银行 (000001.SZ)', 'value': '000001.SZ'}
                            ],
                            style={'width': 200},
                            allowClear=False,
                            defaultValue='600519.SH'
                        ),
                        span=6
                    ),
                    fac.AntdCol(
                        fac.AntdRadioGroup(
                            id='market-period-select',
                            options=[
                                {'label': '日线', 'value': '1d'},
                                {'label': '5分钟', 'value': '5m'},
                                {'label': '1分钟', 'value': '1m'},
                            ],
                            defaultValue='1d',
                            optionType='button'
                        ),
                        span=18,
                        style={'textAlign': 'right'}
                    )
                ],
                align='middle'
            ),
            # K线图容器
            fuc.FefferyDiv(
                id='market-kline-container',
                style={'height': '500px', 'width': '100%'}
            )
        ],
        direction="vertical",
        style=style(width="100%"),
    )
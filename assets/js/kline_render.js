/*
 * K线图渲染逻辑
 * 基于 klinecharts
 */

let KlineChartInstance;

window.dash_clientside = Object.assign({}, window.dash_clientside, {
    kline: {
        renderChart: (
            data_dict, id, nClicks,
            candle_type, show_last_price, show_high_price, show_low_price,
            show_last_value, axis_type, reverse_axis, show_grid
        ) => {
            // 只有当数据有效且触发了更新时才渲染
            if (nClicks > 0 || data_dict) {
                let container = document.getElementById(id);
                if (!container) return window.dash_clientside.no_update;

                // 清空容器防止重复渲染
                // while (container.firstChild) {
                //     container.removeChild(container.firstChild);
                // }

                if (data_dict && data_dict['code'] === 200) {
                    // 清空消息提示
                    let msg_container = document.getElementById('stock-line_message_container');
                    if (msg_container) msg_container.innerHTML = '';

                    let data = data_dict['data']['df'];
                    
                    // 初始化或获取实例
                    if (!KlineChartInstance) {
                        KlineChartInstance = klinecharts.init(id);
                        // 创建指标
                        KlineChartInstance.createIndicator('VOL', false);
                        KlineChartInstance.createIndicator('MACD', false);
                        KlineChartInstance.createIndicator({
                            name: 'MA',
                            calcParams: [5, 10, 30, 60, 120, 250]
                        }, true, { id: 'candle_pane' });
                    }
                    
                    // 更新数据
                    KlineChartInstance.applyNewData(data);

                    // 设置样式
                    KlineChartInstance.setStyles({
                        grid: { show: show_grid },
                        candle: {
                            type: candle_type,
                            tooltip: {
                                custom: [
                                    { title: '时间：', value: '{timestamp}' },
                                    { title: '开：', value: '{open}' },
                                    { title: '高：', value: '{high}' },
                                    { title: '低：', value: '{low}' },
                                    { title: '收：', value: '{close}' },
                                    { title: '量：', value: '{volume}' },
                                    { title: '额：', value: '{turnover}' },
                                ]
                            },
                            priceMark: {
                                high: { show: show_high_price },
                                low: { show: show_low_price },
                                last: { show: show_last_price }
                            }
                        },
                        yAxis: {
                            type: axis_type,
                            reverse: reverse_axis
                        },
                        indicator: {
                            lastValueMark: { show: show_last_value }
                        }
                    });

                    // 自适应大小
                    KlineChartInstance.resize();
                    
                    return window.dash_clientside.no_update;

                } else if (data_dict && data_dict['code'] === 204) {
                    // 处理无数据的情况
                    const msg_component = {
                        type: 'AntdMessage',
                        namespace: 'feffery_antd_components',
                        props: {
                            type: 'warning',
                            content: '未查询到该标的数据，请确认代码是否正确或已运行数据同步任务',
                        }
                    };
                    window.dash_clientside.set_props('stock-line_message_container', { children: msg_component });
                    return window.dash_clientside.no_update;
                }
            }
            return window.dash_clientside.no_update;
        },

        chartChangeSetting: (
            candle_type, show_last_price, show_high_price, show_low_price,
            show_last_value, axis_type, reverse_axis, show_grid
        ) => {
            if (KlineChartInstance) {
                KlineChartInstance.setStyles({
                    grid: { show: show_grid },
                    candle: {
                        type: candle_type,
                        priceMark: {
                            high: { show: show_high_price },
                            low: { show: show_low_price },
                            last: { show: show_last_price }
                        }
                    },
                    yAxis: {
                        type: axis_type,
                        reverse: reverse_axis
                    },
                    indicator: {
                        lastValueMark: { show: show_last_value }
                    }
                });
            }
            return window.dash_clientside.no_update;
        }
    }
});
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
            // 参考示例：https://klinecharts.com/sample/basic
            if (nClicks > 0){
                let container = document.getElementById(id);
                while (container.firstChild) {
                    container.removeChild(container.firstChild);
                }
                // console.log(data_dict)
                if (data_dict['msg']== 'success'){
                    let msg_container = document.getElementById('stock-line_message_container')
                    msg_container.innerHTML = ''
                    let data = data_dict['data']['df']
                    KlineChartInstance = klinecharts.init(id)
                    KlineChartInstance.applyNewData(data)

                    KlineChartInstance.setStyles(
                        {
                            grid: {
                                show: show_grid,
                            },
                            candle: {
                                type: candle_type,
                                // bar:{upColor:'#EF5350',downColor:'#26A69A'}
                                tooltip: {
                                    custom: [
                                        {title: '时间：', value: '{time}'}, 
                                        {title: '开：', value: '{open}'}, 
                                        {title: '高：', value: '{high}'}, 
                                        {title: '低：', value: '{low}'}, 
                                        {title: '收：', value: '{close}'},
                                        {title: '量：', value: '{volume}'},
                                        {title: '额：', value: '{turnover}'},
                                    ]
                                },
                                priceMark: {
                                    high: {
                                        show: show_high_price
                                    },
                                    low: {
                                        show: show_low_price
                                    },
                                    last: {
                                        show: show_last_price
                                    }
                                }
                            },
                            yAxis: {
                                type: axis_type,
                                reverse: reverse_axis
                            },
                            indicator: {
                                lastValueMark: {
                                    show: show_last_value
                                }
                            }

                        }
                    );

                    KlineChartInstance.createIndicator('VOL', false);
                    KlineChartInstance.createIndicator('MACD', false);
                    KlineChartInstance.createIndicator({name: 'MA',calcParams: [5, 10, 30, 60, 120, 250] }, true, {
                        id: 'candle_pane',})
                    
                    // chart.overrideIndicator({name: 'MA',calcParams: [5, 10, 30, 60, 120, 250] },"candle_pane");
                    KlineChartInstance.setMaxOffsetLeftDistance(20);
                    KlineChartInstance.setMaxOffsetRightDistance(20);

                    // 实现随容器尺寸变化而自动重绘
                    const observer = new ResizeObserver((entries) => {
                        KlineChartInstance.resize()
                    });
                    observer.observe(container)
                    // chartInstances[id] = chart
                    return window.dash_clientside.no_update
                } else {
                    // conatiner.innerHTML = ''
                    // console.log('未查询到数据')
                    // window.dash_clientside.set_props(
                    //     id,
                    //     // { checked: false }
                    //     {
                    //         // "children": '未查询到数据'
                    //         "children" : {
                    //             type: 'AntdEmpty', 
                    //             namespace: 'feffery_antd_components',
                    //             props: {
                    //                 'description' : '未查询到数据'
                    //             }
                    //         }
                    //     },
                    // )
                    // return window.dash_clientside.no_update
                    const msg_component = {
                        type: 'AntdMessage', 
                        namespace: 'feffery_antd_components',
                        props: {
                            type : 'warning',
                            content : '未查询到数据',
                        }
                    };
                    window.dash_clientside.set_props('stock-line_message_container', { children: msg_component });
                    return window.dash_clientside.no_update
                }
            }else{
                return window.dash_clientside.no_update
            }
            
        },
        chartChangeSetting: (
            candle_type, show_last_price, show_high_price, show_low_price,
            show_last_value, axis_type, reverse_axis, show_grid
        ) => {
            if (KlineChartInstance){
                KlineChartInstance.setStyles({
                    grid: {
                        show: show_grid
                    },
                    candle: {
                        type: candle_type,
                        priceMark: {
                            high: {
                                show: show_high_price
                            },
                            low: {
                                show: show_low_price
                            },
                            last: {
                                show: show_last_price
                            }
                        }
                    },
                    yAxis: {
                        type: axis_type,
                        reverse: reverse_axis
                    },
                    indicator: {
                        lastValueMark: {
                            show: show_last_value
                        }
                    }

                })
            }
            return window.dash_clientside.no_update
        }
    }
});
/*
 * K线图渲染逻辑
 * 基于 klinecharts
 */

let KlineChartInstance;
let activeMainIndicator = 'NONE'; // 记录当前的主图指标
let activeSubIndicators = [];     // 记录当前的副图指标
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

                    activeMainIndicator = 'MA';
                    activeSubIndicators = []; // 每次重新 init 时清空状态

                    KlineChartInstance.applyNewData(data)

                    KlineChartInstance.setStyles(
                        {
                            grid: {
                                show: show_grid,
                            },
                            candle: {
                                type: candle_type,
                                bar: {
                                    // 'current_open' | 'previous_close'
                                    compareRule: 'current_open',
                                    upColor: '#F92855',
                                    downColor: '#2DC08E',
                                    noChangeColor: '#888888',
                                    upBorderColor: '#F92855',
                                    downBorderColor: '#2DC08E',
                                    noChangeBorderColor: '#888888',
                                    upWickColor: '#F92855',
                                    downWickColor: '#2DC08E',
                                    noChangeWickColor: '#888888'
                                    },
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
                                },
                                // ======= 新增 Tooltip 图标配置 =======
                                tooltip: {
                                    icons: [
                                        {
                                            id: 'setting', // 必须与下方事件监听的 id 一致
                                            position: 'middle',
                                            marginLeft: 6,
                                            marginTop: 4,
                                            marginRight: 6,
                                            marginBottom: 0,
                                            size: 14,
                                            icon: '⚙', // 使用标准的 Unicode 齿轮符号
                                            color: '#76808F',
                                            activeColor: '#26A69A'
                                        }
                                    ]
                                }
                            }

                        }
                    );

                    // 2. 初始化默认副图指标，并记录到全局状态中
                    const defaultSubs = ['VOL', 'MACD'];
                    defaultSubs.forEach(name => {
                        KlineChartInstance.createIndicator(name, false, { id: `pane_${name}` });
                        activeSubIndicators.push(name);
                    });

                    KlineChartInstance.createIndicator({name: 'MA',calcParams: [5, 30, 120, 250] }, true, {
                        id: 'candle_pane',})

                    

                    // chart.overrideIndicator({name: 'MA',calcParams: [5, 10, 30, 60, 120, 250] },"candle_pane");
                    KlineChartInstance.setMaxOffsetLeftDistance(20);
                    KlineChartInstance.setMaxOffsetRightDistance(20);

                    // 实现随容器尺寸变化而自动重绘
                    const observer = new ResizeObserver((entries) => {
                        KlineChartInstance.resize()
                    });
                    observer.observe(container)


                    // ======= 新增：订阅指标提示框图标点击事件 =======
                    KlineChartInstance.subscribeAction('onTooltipIconClick', (data) => {
                        if (data.iconId === 'setting' && data.indicatorName) {
                            const paneId = data.paneId;
                            const indicatorName = data.indicatorName;

                            // 1. 获取该指标当前正在使用的参数
                            const indicatorInstance = KlineChartInstance.getIndicatorByPaneId(paneId, indicatorName);
                            const currentParams = indicatorInstance ? indicatorInstance.calcParams : [];

                            // 2. 弹出原生输入框让用户修改（例如输入: 5, 10, 30）
                            const newParamsStr = prompt(
                                `修改 ${indicatorName} 的指标参数 (当前: ${currentParams.join(', ')})，用英文逗号隔开：`,
                                currentParams.join(',')
                            );

                            // 3. 用户点击确定且输入不为空时执行覆写
                            if (newParamsStr !== null) {
                                // 解析字符串为数字数组
                                const newParams = newParamsStr.split(',').map(v => {
                                    const num = Number(v.trim());
                                    return isNaN(num) ? v.trim() : num;
                                });

                                try {
                                    // 4. 核心API：覆写图表上的指标参数，图表会自动局部重绘
                                    KlineChartInstance.overrideIndicator({
                                        name: indicatorName,
                                        calcParams: newParams
                                    }, paneId);
                                } catch (error) {
                                    console.error("修改指标参数失败:", error);
                                }
                            }
                        }
                    });
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
        },
        updateIndicators: function(mainIndicator, subIndicators) {
            const chart = KlineChartInstance;
            if (!chart) return window.dash_clientside.no_update;

            subIndicators = subIndicators || []; // 防御性处理，防止传入 null

            // =========================
            // 1. 处理主图指标 (精准更新：只在发生变化时执行)
            // =========================
            if (mainIndicator !== activeMainIndicator) {
                // 移除旧的主图指标（通过指定名称精准移除，避免清空其他主图元素）
                if (activeMainIndicator && activeMainIndicator !== 'NONE') {
                    try {
                        chart.removeIndicator('candle_pane', activeMainIndicator);
                    } catch (e) { console.warn(e); }
                }
                
                // 添加新的主图指标
                if (mainIndicator && mainIndicator !== 'NONE') {
                    chart.createIndicator(mainIndicator, true, { id: 'candle_pane' });
                }
                
                // 更新主图状态
                activeMainIndicator = mainIndicator;
            }

            // =========================
            // 2. 处理副图指标 (差异对比：只对增删的项操作)
            // =========================
            // 找出需要删除的指标：在老列表中，但不在新列表中
            const toRemove = activeSubIndicators.filter(name => !subIndicators.includes(name));
            // 找出需要添加的指标：在新列表中，但不在老列表中
            const toAdd = subIndicators.filter(name => !activeSubIndicators.includes(name));

            // 执行删除操作，不动其他未改变的 Pane
            toRemove.forEach(name => {
                try {
                    chart.removeIndicator(`pane_${name}`);
                } catch(e) {
                    console.warn(`移除副图 ${name} 失败:`, e);
                }
            });

            // 执行新增操作
            toAdd.forEach(name => {
                chart.createIndicator(name, false, { id: `pane_${name}` });
            });

            // 同步最新状态
            activeSubIndicators = [...subIndicators];

            return window.dash_clientside.no_update;
        }
    }
});
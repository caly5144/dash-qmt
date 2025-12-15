import pandas as pd
import time
from datetime import datetime, timedelta
from models.trade_models import TradeRecord, trade_db
from xtquant import xtconstant
from utils.fee_calculator import FeeCalculator
from utils.stock_info_manager import stock_info_manager

# Excel 文件路径 (修改为你实际的文件名)
EXCEL_PATH = '交割单.xlsx' 

def process_stock_code(code):
    """
    自动为代码添加后缀
    规则：
    6开头 -> .SH
    0, 3开头 -> .SZ
    5开头 (ETF/基金) -> .SH (通常沪市ETF)
    15, 16 (ETF/LOF) -> .SZ (深市)
    北交所 8, 4 -> .BJ (视具体情况，这里做简单处理)
    """
    code = str(code).strip()
    if '.' in code:
        return code
    
    if code.startswith('6') or code.startswith('5'): # 沪市股票及ETF
        return f"{code}.SH"
    elif code.startswith('0') or code.startswith('3') or code.startswith('1'): # 深市股票及ETF
        return f"{code}.SZ"
    elif code.startswith('8') or code.startswith('4'): # 北交所
        return f"{code}.BJ"
    
    return f"{code}.SH" # 默认兜底，可视情况修改

def parse_direction(op_flag, volume):
    """
    解析买卖方向 (order_type) 和 side
    op_flag: 业务标志 (证券买入/证券卖出)
    volume: 发生数量 (正数/负数)
    """
    op = str(op_flag).strip()
    
    # 根据业务标志判断
    if '买入' in op:
        return xtconstant.STOCK_BUY, 1
    elif '卖出' in op:
        return xtconstant.STOCK_SELL, -1
    
    # 如果标志不清晰，根据数量正负判断
    if volume > 0:
        return xtconstant.STOCK_BUY, 1
    elif volume < 0:
        return xtconstant.STOCK_SELL, -1
        
    return xtconstant.STOCK_BUY, 1 # 默认

def import_excel():
    print(f"正在读取文件: {EXCEL_PATH} ...")
    try:
        # 读取 Excel，确保代码列作为字符串读取，防止前导0丢失
        df = pd.read_excel(EXCEL_PATH, dtype={'证券代码': str, '股东账号': str})
    except FileNotFoundError:
        print(f"错误: 找不到文件 {EXCEL_PATH}，请确保文件在当前目录下。")
        return

    records_to_insert = []
    
    print("开始解析数据...")
    for index, row in df.iterrows():
        try:
            # 1. 处理日期时间
            date_str = str(row['日期']).split(' ')[0] # 只取日期部分 YYYY-MM-DD
            trade_time = datetime.strptime(date_str, '%Y-%m-%d')
            # 加上 15:00:00
            trade_time = trade_time.replace(hour=15, minute=0, second=0)
            
            # 2. 处理代码
            raw_code = row['证券代码']
            stock_code = process_stock_code(raw_code)
            stock_name = stock_info_manager.get_stock_name(stock_code)
            
            # 3. 处理数值
            volume = float(row['发生数量'])
            price = float(row['成交均价'])
            amount = abs(float(row['成交金额'])) # 数据库存绝对值
            commission = float(row.get('佣金', 0)) + float(row.get('印花税', 0)) + float(row.get('其他费用', 0))
            
            # 4. 确定方向
            op_flag = row['业务标志']
            order_type, side = parse_direction(op_flag, volume)
            
            # 5. 生成唯一ID (使用 日期+代码+价格+方向 组合哈希，防止重复导入)
            # 注意：如果同一天同一代码同一价格有多笔，这种简易ID可能会冲突。
            # 更好的方式是 Excel 如果有“合同编号”列，直接用合同编号。
            # 既然截图中没有合同编号，我们构造一个独特的 ID：
            unique_str = f"{date_str}_{stock_code}_{price}_{abs(volume)}_{side}"
            
            # 检查是否已存在
            if TradeRecord.select().where(TradeRecord.traded_id == unique_str).exists():
                print(f"跳过重复记录: {date_str} {stock_code}")
                continue
        
            fees = FeeCalculator.calculate_all_fees(stock_code, price, abs(volume), side)

            # 6. 构建模型对象
            record = {
                'traded_id': unique_str,
                'order_id': f"IMPORT_{int(time.time())}_{index}", # 虚拟订单ID
                'stock_code': stock_code,
                'stock_name': stock_name,
                'trade_time': trade_time,
                'trade_date': trade_time.strftime('%Y-%m-%d'),
                'order_type': order_type,
                'direction': None, # 默认为多
                'offset_flag': None, # 默认为开
                'price': price,
                'volume': int(abs(volume)), # 存绝对值
                'amount': amount,
                'commission': fees['commission'],
                'stamp_duty': fees['stamp_duty'],
                'other_fees': fees['other_fees'],
                'total_fees': fees['total_fees'],
                'side': side,
                'strategy_name': '手动下单',
                'source': 'excel',
                'remark': None
            }
            records_to_insert.append(record)
            
        except Exception as e:
            print(f"解析第 {index+1} 行出错: {e}")
            continue

    # 批量入库
    if records_to_insert:
        print(f"准备插入 {len(records_to_insert)} 条记录...")
        with trade_db.atomic():
            # 使用 chunked 避免 SQL 语句过长
            for idx in range(0, len(records_to_insert), 100):
                TradeRecord.insert_many(records_to_insert[idx:idx+100]).execute()
        print("导入完成！")
    else:
        print("没有新的记录需要导入。")

if __name__ == '__main__':
    # 确保表存在
    if not trade_db.table_exists('traderecord'):
        trade_db.connect()
        trade_db.create_tables([TradeRecord])
        
    import_excel()
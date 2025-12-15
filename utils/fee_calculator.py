import re
from configs.fee_config import fee_manager

class FeeCalculator:
    @staticmethod
    def identify_market_product(stock_code):
        """
        根据代码识别市场和品种
        返回: (market, product_type)
        """
        code = stock_code.upper()
        
        # 1. 识别市场
        if code.endswith('.SH'):
            market = "SH"
        elif code.endswith('.SZ'):
            market = "SZ"
        elif code.endswith('.BJ'):
            market = "BJ"
        else:
            market = "SH" # 默认

        # 2. 识别品种 (简单规则，可根据实际需求扩展)
        # 沪市: 60/68开头是股票, 5开头是ETF/基金, 11开头是可转债
        # 深市: 00/30开头是股票, 15开头是ETF/LOF, 12开头是可转债
        # 北交所: 8/4开头
        number_part = code.split('.')[0]
        
        if market == "SH":
            if number_part.startswith(('5', '51', '56', '58')):
                product = "ETF"
            elif number_part.startswith(('11', '10')): # 11转债
                product = "BOND"
            else:
                product = "STOCK"
        elif market == "SZ":
            if number_part.startswith(('15', '16')):
                product = "ETF"
            elif number_part.startswith('12'):
                product = "BOND"
            else:
                product = "STOCK"
        elif market == "BJ":
            product = "STOCK"
        else:
            product = "STOCK"
            
        return market, product

    @staticmethod
    def calculate_single_fee(amount, config, direction_side):
        """
        计算单项费用
        amount: 交易金额
        config: 费率配置项 (dict)
        direction_side: 1(买入), -1(卖出)
        """
        mode = config.get("mode", "both")
        
        # 判断是否收取
        should_charge = False
        if mode == "both":
            should_charge = True
        elif mode == "buy" and direction_side == 1:
            should_charge = True
        elif mode == "sell" and direction_side == -1:
            should_charge = True
            
        if not should_charge:
            return 0.0
            
        fee = round(amount * config.get("rate", 0), 2)
        min_fee = config.get("min_fee", 0)
        
        return max(fee, min_fee)

    @classmethod
    def calculate_all_fees(cls, stock_code, price, volume, direction_side):
        """
        计算所有费用
        direction_side: 1 (买入), -1 (卖出)
        """
        market, product = cls.identify_market_product(stock_code)
        config = fee_manager.get_config()
        
        # 获取对应产品配置，如果没有则使用默认兜底（防止报错）
        market_config = config.get(market, config.get("SH"))
        product_config = market_config.get(product, market_config.get("STOCK"))
        
        amount = price * volume
        
        commission = cls.calculate_single_fee(amount, product_config["commission"], direction_side)
        stamp_duty = cls.calculate_single_fee(amount, product_config["stamp_duty"], direction_side)
        other_fees = cls.calculate_single_fee(amount, product_config["other_fees"], direction_side)
        
        total_fees = commission + stamp_duty + other_fees
        
        return {
            "commission": round(commission, 4),
            "stamp_duty": round(stamp_duty, 4),
            "other_fees": round(other_fees, 4),
            "total_fees": round(total_fees, 4)
        }
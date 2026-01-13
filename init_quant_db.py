from models.trade_models import TradeRecord
from models.market_models import KlineData
print("Quant databases initialized.")

from utils.tushare_api import TushareAPI

api = TushareAPI()
api.save_trade_date('20010101')
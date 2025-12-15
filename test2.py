from models.market_models import KlineData, market_db
import pandas as pd

adict = KlineData.select().where(KlineData.stock_code == '000001.SZ').order_by(KlineData.date).dicts()

df = pd.DataFrame(list(adict))
df.to_excel('test.xlsx', index=False)
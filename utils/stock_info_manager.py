import json
from pathlib import Path
from xtquant import xtdata

# 缓存文件路径
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_FILE = DATA_DIR / "stock_names.json"

class StockInfoManager:
    _instance = None
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StockInfoManager, cls).__new__(cls)
            cls._instance.load_cache()
        return cls._instance

    def load_cache(self):
        """加载本地缓存"""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
            except Exception as e:
                print(f"【StockInfo】加载缓存失败: {e}")
                self._cache = {}
        else:
            self._cache = {}

    def save_cache(self):
        """保存缓存到本地"""
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False)
        except Exception as e:
            print(f"【StockInfo】保存缓存失败: {e}")

    def refresh_mapping(self):
        """
        全量更新代码名称映射
        从 xtdata 获取 沪深A股、ETF、可转债 等板块数据
        """
        print("【StockInfo】开始更新证券代码映射...")
        xtdata.enable_hello = False
        # 定义需要获取的板块
        target_sectors = [
            '沪深A股', '沪深ETF', '沪深转债', '沪深指数', 
            '北交所'
        ]
        
        # 获取所有相关板块的成分股并去重
        all_codes = set()
        for sector in target_sectors:
            try:
                codes = xtdata.get_stock_list_in_sector(sector)
                if codes:
                    all_codes.update(codes)
            except:
                pass
        
        xtdata.download_history_contracts() # 下载已退市合约数据
        # 批量获取合约信息 (xtdata 没有批量获取名称的简单接口，只能遍历 get_instrument_detail)
        # 注意：如果有几千只股票，循环调用可能会慢，但这是纯本地操作(MiniQMT缓存)，通常很快
        new_map = {}
        for code in all_codes:
            detail = xtdata.get_instrument_detail(code)
            if detail and 'InstrumentName' in detail:
                new_map[code] = detail['InstrumentName']
        
        # 更新内存和文件
        self._cache.update(new_map)
        self.save_cache()
        print(f"【StockInfo】更新完成，共收录 {len(self._cache)} 条证券信息")
        return len(self._cache)

    def get_stock_name(self, stock_code):
        """获取证券名称，如果缓存没有，尝试实时获取并更新"""
        # 1. 查缓存
        if stock_code in self._cache:
            return self._cache[stock_code]
        
        # 2. 缓存未命中，尝试实时获取
        try:
            detail = xtdata.get_instrument_detail(stock_code)
            if detail and 'InstrumentName' in detail:
                name = detail['InstrumentName']
                # 更新缓存
                self._cache[stock_code] = name
                self.save_cache()
                return name
        except:
            pass
            
        return stock_code # 实在找不到，返回代码本身

# 全局单例
stock_info_manager = StockInfoManager()
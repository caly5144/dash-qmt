import json
from pathlib import Path

# 配置文件路径
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = DATA_DIR / "fees_config.json"

# 默认费率配置
DEFAULT_FEES = {
    "SH": {  # 上海市场
        "STOCK": {  # A股
            "commission": {"rate": 0.0001, "min_fee": 5.0, "mode": "both"}, # 佣金: 万2.5, 最低5元, 双边
            "stamp_duty": {"rate": 0.0005, "min_fee": 0.0, "mode": "sell"},  # 印花税: 万5, 卖方
            "other_fees": {"rate": 0.00001, "min_fee": 0.0, "mode": "both"}  # 过户费等: 万0.1
        },
        "ETF": {
            "commission": {"rate": 0.0001, "min_fee": 5, "mode": "both"},  # ETF通常免印花税
            "stamp_duty": {"rate": 0.0, "min_fee": 0.0, "mode": "none"},
            "other_fees": {"rate": 0.0, "min_fee": 0.0, "mode": "none"}
        },
        "BOND": { # 可转债
            "commission": {"rate": 0.00004, "min_fee": 0.0, "mode": "both"},
            "stamp_duty": {"rate": 0.0, "min_fee": 0.0, "mode": "none"},
            "other_fees": {"rate": 0.0, "min_fee": 0.0, "mode": "none"}
        }
    },
    "SZ": {  # 深圳市场
        "STOCK": {
            "commission": {"rate": 0.0001, "min_fee": 5.0, "mode": "both"},
            "stamp_duty": {"rate": 0.0005, "min_fee": 0.0, "mode": "sell"},
            "other_fees": {"rate": 0.00001, "min_fee": 0.0, "mode": "both"}
        },
        "ETF": {
            "commission": {"rate": 0.0001, "min_fee": 5.0, "mode": "both"},
            "stamp_duty": {"rate": 0.0, "min_fee": 0.0, "mode": "none"},
            "other_fees": {"rate": 0.0, "min_fee": 0.0, "mode": "none"}
        },
        "BOND": {
            "commission": {"rate": 0.00004, "min_fee": 0.0, "mode": "both"},
            "stamp_duty": {"rate": 0.0, "min_fee": 0.0, "mode": "none"},
            "other_fees": {"rate": 0.0, "min_fee": 0.0, "mode": "none"}
        }
    },
    "BJ": { # 北交所
        "STOCK": {
            "commission": {"rate": 0.0001, "min_fee": 5.0, "mode": "both"},
            "stamp_duty": {"rate": 0.0005, "min_fee": 0.0, "mode": "sell"},
            "other_fees": {"rate": 0.0, "min_fee": 0.0, "mode": "none"}
        }
    }
}

class FeeConfigManager:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FeeConfigManager, cls).__new__(cls)
            cls._instance.load_config()
        return cls._instance

    def load_config(self):
        """加载配置，如果不存在则创建默认配置"""
        if not CONFIG_PATH.exists():
            self._config = DEFAULT_FEES
            self.save_config()
            print(f"已生成默认费率配置文件: {CONFIG_PATH}")
        else:
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except Exception as e:
                print(f"加载费率配置失败，使用默认配置: {e}")
                self._config = DEFAULT_FEES

    def save_config(self):
        """保存配置到文件"""
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=4, ensure_ascii=False)

    def get_config(self):
        return self._config

    def update_config(self, new_config):
        self._config = new_config
        self.save_config()

# 全局单例
fee_manager = FeeConfigManager()
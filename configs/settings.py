import json
from pathlib import Path

# 定义路径
BASE_DIR = Path(__file__).parent.parent
SECRET_DIR = BASE_DIR / "secrets"
SECRET_FILE = SECRET_DIR / "config.json"

# 默认配置（当配置文件不存在时使用，作为模板）
DEFAULT_CONFIG = {
    "MINI_QMT_PATH": r"D:\迅投极速交易终端 睿智融科版\userdata_mini",
    "ACCOUNT_ID": "88888888",
    "APP_SECRET_KEY": "magic-dash-pro-demo"
}

def load_config():
    """加载敏感配置，如果文件不存在则自动创建"""
    if not SECRET_FILE.exists():
        # 自动创建目录
        if not SECRET_DIR.exists():
            SECRET_DIR.mkdir(parents=True, exist_ok=True)
        
        # 生成默认配置文件
        try:
            with open(SECRET_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
            print(f"已生成默认配置文件: {SECRET_FILE}，请前往修改真实信息。")
        except Exception as e:
            print(f"无法创建配置文件: {e}")
            return DEFAULT_CONFIG
        
        return DEFAULT_CONFIG
    
    try:
        with open(SECRET_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取配置文件失败: {e}，将使用默认配置")
        return DEFAULT_CONFIG

# 加载配置到内存，供其他模块导入
GLOBAL_SECRETS = load_config()
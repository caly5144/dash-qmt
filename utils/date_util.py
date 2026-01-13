import json
from configs.settings import DATA_DIR

def jsonKeys2int(x):
    """
    加载json时，字典key转为int型
    使用方法：json.loads(jsonDict, object_hook=jsonKeys2int)
    """
    
    if isinstance(x, dict):
        return {int(k):v for k,v in x.items()}
    return x

json_path = PROGRAMPATH / './data/trade_date.json'
DATEDICT = load_json(json_path,object_hook=jsonKeys2int)


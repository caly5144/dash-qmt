import os
from typing import Literal


class DatabaseConfig:
    """数据库配置参数"""

    # 应用基础数据库类型
    # 当使用postgresql类型时，请使用`pip install psycopg2-binary`安装必要依赖
    # 当使用mysql类型时，请使用`pip install pymysql`安装必要依赖
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, 'data')

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"已自动创建数据目录: {DATA_DIR}")

    database_type: Literal["sqlite", "postgresql", "mysql"] = "sqlite"

    system_db_name = os.path.join(DATA_DIR, "magic_dash_pro.db")
    market_db_name = os.path.join(DATA_DIR, "market_data.db")
    trade_db_name = os.path.join(DATA_DIR, "trade_data.db")

    # 当database_type为'postgresql'时，对应的数据库连接配置参数，使用时请根据实际情况修改
    postgresql_config = {
        "host": "127.0.0.1",
        "port": 5432,
        "user": "postgres",
        "password": "admin123",
        "database": "magic_dash_pro",
    }

    # 当database_type为'mysql'时，对应的数据库连接配置参数，使用时请根据实际情况修改
    mysql_config = {
        "host": "127.0.0.1",
        "port": 3306,
        "user": "root",
        "password": "admin123",
        "database": "magic_dash_pro",
    }

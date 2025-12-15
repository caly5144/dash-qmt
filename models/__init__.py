from peewee import SqliteDatabase, Model
from feffery_dash_utils.version_utils import check_dependencies_version
from playhouse.pool import PooledPostgresqlExtDatabase, PooledMySQLDatabase

from configs.database_config import DatabaseConfig


def get_db(db_name):
    """根据配置参数，创建数据库连接对象"""

    if DatabaseConfig.database_type == "sqlite":
        return SqliteDatabase(db_name)
    elif DatabaseConfig.database_type == "postgresql":
        # 必要依赖检查
        check_dependencies_version(
            rules=[
                {
                    "name": "psycopg2-binary",
                }
            ]
        )

        # 返回postgresql类型连接池对象
        return PooledPostgresqlExtDatabase(
            host=DatabaseConfig.postgresql_config["host"],
            port=DatabaseConfig.postgresql_config["port"],
            userel=DatabaseConfig.postgresql_config["user"],
            password=DatabaseConfig.postgresql_config["password"],
            database=DatabaseConfig.postgresql_config["database"],
            max_connections=32,
            stale_timeout=300,
        )

    elif DatabaseConfig.database_type == "mysql":
        # 必要依赖检查
        check_dependencies_version(
            rules=[
                {
                    "name": "pymysql",
                }
            ]
        )

        # 返回mysql类型连接池对象
        return PooledMySQLDatabase(
            host=DatabaseConfig.mysql_config["host"],
            port=DatabaseConfig.mysql_config["port"],
            user=DatabaseConfig.mysql_config["user"],
            passwd=DatabaseConfig.mysql_config["password"],
            database=DatabaseConfig.mysql_config["database"],
            max_connections=32,
            stale_timeout=300,
        )

    # # 默认返回sqlite类型连接对象
    # return SqliteDatabase("magic_dash_pro.db")


# 创建数据库连接对象
sys_db = get_db(DatabaseConfig.system_db_name)
market_db = get_db(DatabaseConfig.market_db_name)
trade_db = get_db(DatabaseConfig.trade_db_name)

db = sys_db


class BaseModel(Model):
    """系统表基类"""
    class Meta:
        database = sys_db

class MarketBaseModel(Model):
    """行情表基类"""
    class Meta:
        database = market_db

class TradeBaseModel(Model):
    """交易表基类"""
    class Meta:
        database = trade_db

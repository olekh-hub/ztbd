from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"


class DatabaseTarget(StrEnum):
    MYSQL = "mysql"
    POSTGRES = "postgres"
    MONGO = "mongo"
    REDIS = "redis"


class IndexVariant(StrEnum):
    NO_IDX = "no_idx"
    IDX = "idx"


@dataclass(frozen=True)
class DataSizeProfile:
    name: str
    customers: int
    orders: int
    reviews: int


SIZE_PROFILES = {
    "test": DataSizeProfile(name="test", customers=5, orders=10, reviews=8),
    "s": DataSizeProfile(name="s", customers=50_000, orders=500_000, reviews=500_000),
    "m": DataSizeProfile(name="m", customers=100_000, orders=1_000_000, reviews=1_000_000),
    "l": DataSizeProfile(name="l", customers=200_000, orders=10_000_000, reviews=1_000_000),
}


@dataclass(frozen=True)
class MySqlSettings:
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = "password"
    database: str = "ecommerce_db"


@dataclass(frozen=True)
class PostgresSettings:
    host: str = "localhost"
    port: int = 5432
    user: str = "admin"
    password: str = "password"
    database: str = "ecommerce_db"


@dataclass(frozen=True)
class MongoSettings:
    uri: str = "mongodb://localhost:27017"
    database: str = "ecommerce_db"


@dataclass(frozen=True)
class RedisSettings:
    host: str = "localhost"
    port: int = 6379
    db: int = 0


@dataclass(frozen=True)
class AppSettings:
    data_dir: Path = DEFAULT_DATA_DIR
    order_batch_size: int = 50_000
    mysql: MySqlSettings = MySqlSettings()
    postgres: PostgresSettings = PostgresSettings()
    mongo: MongoSettings = MongoSettings()
    redis: RedisSettings = RedisSettings()

import mysql.connector
import psycopg
import redis
from pymongo import MongoClient

from ztbd.config import AppSettings, DatabaseTarget
from ztbd.repositories.mongo import MongoDocumentRepository
from ztbd.repositories.mysql import MySqlIngestRepository
from ztbd.repositories.postgres import PostgresIngestRepository
from ztbd.repositories.redis_repo import RedisKeyValueRepository


def create_relational_repository(target: DatabaseTarget, settings: AppSettings):
    if target == DatabaseTarget.MYSQL:
        connection = mysql.connector.connect(
            host=settings.mysql.host,
            port=settings.mysql.port,
            user=settings.mysql.user,
            password=settings.mysql.password,
            database=settings.mysql.database,
            allow_local_infile=True,
        )
        return MySqlIngestRepository(connection)

    if target == DatabaseTarget.POSTGRES:
        connection = psycopg.connect(
            host=settings.postgres.host,
            port=settings.postgres.port,
            user=settings.postgres.user,
            password=settings.postgres.password,
            dbname=settings.postgres.database,
        )
        return PostgresIngestRepository(connection)

    raise ValueError(f"{target} is not a relational target")


def create_mongo_repository(settings: AppSettings) -> MongoDocumentRepository:
    client = MongoClient(settings.mongo.uri)
    return MongoDocumentRepository(client[settings.mongo.database])


def create_redis_repository(settings: AppSettings) -> RedisKeyValueRepository:
    client = redis.Redis(
        host=settings.redis.host,
        port=settings.redis.port,
        db=settings.redis.db,
        decode_responses=True,
    )
    return RedisKeyValueRepository(client)

import argparse
import random
from pathlib import Path

from faker import Faker

from ztbd.config import (
    DEFAULT_DATA_DIR,
    SIZE_PROFILES,
    AppSettings,
    DatabaseTarget,
    MongoSettings,
    MySqlSettings,
    PostgresSettings,
    RedisSettings,
)
from ztbd.csv_store import CsvStore
from ztbd.generation import DataGenerator
from ztbd.ingestion import IngestionService
from ztbd.repositories.factory import create_mongo_repository, create_redis_repository, create_relational_repository


def parse_targets(raw_targets: list[str]) -> set[DatabaseTarget]:
    targets = set(raw_targets)
    if "all" in targets:
        return {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO, DatabaseTarget.REDIS}
    if "nosql" in targets:
        targets.remove("nosql")
        targets.update({"mongo", "redis"})
    return {DatabaseTarget(target) for target in targets}


def build_settings(args: argparse.Namespace) -> AppSettings:
    return AppSettings(
        data_dir=args.data_dir.resolve(),
        order_batch_size=args.order_batch_size,
        mysql=MySqlSettings(
            host=args.mysql_host,
            port=args.mysql_port,
            user=args.mysql_user,
            password=args.mysql_password,
            database=args.mysql_database,
        ),
        postgres=PostgresSettings(
            host=args.postgres_host,
            port=args.postgres_port,
            user=args.postgres_user,
            password=args.postgres_password,
            database=args.postgres_database,
        ),
        mongo=MongoSettings(uri=args.mongo_uri, database=args.mongo_database),
        redis=RedisSettings(host=args.redis_host, port=args.redis_port, db=args.redis_db),
    )


def run_generate(args: argparse.Namespace) -> None:
    profile = SIZE_PROFILES[args.size]
    faker = Faker("en_US")
    faker.seed_instance(args.seed)
    generator = DataGenerator(
        profile=profile,
        store=CsvStore(args.out_dir.resolve()),
        faker=faker,
        rng=random.Random(args.seed),
    )
    generator.generate()
    print(f"Generated {profile.name} data in {args.out_dir}")


def run_ingest(args: argparse.Namespace) -> None:
    settings = build_settings(args)
    targets = parse_targets(args.targets)
    relational = {}
    if DatabaseTarget.MYSQL in targets:
        relational[DatabaseTarget.MYSQL] = create_relational_repository(DatabaseTarget.MYSQL, settings)
    if DatabaseTarget.POSTGRES in targets:
        relational[DatabaseTarget.POSTGRES] = create_relational_repository(DatabaseTarget.POSTGRES, settings)

    service = IngestionService(
        settings=settings,
        store=CsvStore(settings.data_dir),
        relational_repositories=relational,
        document_repository=create_mongo_repository(settings) if DatabaseTarget.MONGO in targets else None,
        key_value_repository=create_redis_repository(settings) if DatabaseTarget.REDIS in targets else None,
    )
    service.run(targets)
    print("Done")


def add_ingest_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--targets",
        nargs="+",
        default=["all"],
        choices=["all", "mysql", "postgres", "mongo", "redis", "nosql"],
        help="Database targets to ingest. Defaults to all.",
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--order-batch-size", type=int, default=50_000)
    parser.add_argument("--mysql-host", default="localhost")
    parser.add_argument("--mysql-port", type=int, default=3306)
    parser.add_argument("--mysql-user", default="root")
    parser.add_argument("--mysql-password", default="password")
    parser.add_argument("--mysql-database", default="ecommerce_db")
    parser.add_argument("--postgres-host", default="localhost")
    parser.add_argument("--postgres-port", type=int, default=5432)
    parser.add_argument("--postgres-user", default="admin")
    parser.add_argument("--postgres-password", default="password")
    parser.add_argument("--postgres-database", default="ecommerce_db")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--mongo-database", default="ecommerce_db")
    parser.add_argument("--redis-host", default="localhost")
    parser.add_argument("--redis-port", type=int, default=6379)
    parser.add_argument("--redis-db", type=int, default=0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ZTBD data generation and ingestion tooling.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate ecommerce CSV data.")
    generate.add_argument("--size", choices=SIZE_PROFILES.keys(), default="l")
    generate.add_argument("--out-dir", type=Path, default=DEFAULT_DATA_DIR)
    generate.add_argument("--seed", type=int, default=42)
    generate.set_defaults(func=run_generate)

    ingest = subparsers.add_parser("ingest", help="Ingest generated CSV data.")
    add_ingest_args(ingest)
    ingest.set_defaults(func=run_ingest)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

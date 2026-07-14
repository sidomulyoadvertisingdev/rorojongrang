import os

import pymysql
from sqlalchemy import text

from config.settings import DB_CONFIG
from models import db
from models.user import User
from utils.logger import get_logger

logger = get_logger("bootstrap")

TASK_COLUMNS = [
    ("search_radius", "INT DEFAULT 5"),
    ("country", "VARCHAR(100) DEFAULT 'Indonesia'"),
    ("province", "VARCHAR(100)"),
    ("regency", "VARCHAR(100)"),
    ("district", "VARCHAR(100)"),
    ("center_lat", "DOUBLE"),
    ("center_lng", "DOUBLE"),
]

BUSINESS_COLUMNS = [
    ("lead_status", "VARCHAR(30) DEFAULT 'new'"),
    ("lead_note", "TEXT"),
    ("lead_score", "INT DEFAULT 0"),
    ("last_contacted_at", "DATETIME"),
]

USER_COLUMNS = [
    ("google_id", "VARCHAR(100) UNIQUE"),
    ("avatar_url", "VARCHAR(500)"),
]


def ensure_database_exists():
    connection = pymysql.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        autocommit=True,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        connection.close()


def seed_default_admin():
    admin_username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@rorojonggrang.com")
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
    admin_full_name = os.getenv("DEFAULT_ADMIN_FULL_NAME", "Administrator")

    user = User.query.filter(
        (User.username == admin_username) | (User.email == admin_email)
    ).first()
    if user:
        return user

    user = User(
        username=admin_username,
        email=admin_email,
        full_name=admin_full_name,
        is_admin=True,
    )
    user.set_password(admin_password)
    db.session.add(user)
    db.session.commit()

    logger.info("Seeded default admin user: %s", admin_email)
    return user


def _table_columns(table_name: str) -> set[str]:
    result = db.session.execute(
        text(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table_name
            """
        ),
        {"schema": DB_CONFIG["database"], "table_name": table_name},
    )
    return {row[0] for row in result.fetchall()}


def migrate_scraping_tasks_schema():
    existing_columns = _table_columns("scraping_tasks")
    for col_name, col_def in TASK_COLUMNS:
        if col_name in existing_columns:
            continue
        try:
            db.session.execute(
                text(f"ALTER TABLE scraping_tasks ADD COLUMN {col_name} {col_def}")
            )
            db.session.commit()
            logger.info("Added missing scraping_tasks column: %s", col_name)
        except Exception as exc:
            db.session.rollback()
            logger.warning("Could not add column %s: %s", col_name, exc)


def migrate_businesses_schema():
    existing_columns = _table_columns("businesses")
    for col_name, col_def in BUSINESS_COLUMNS:
        if col_name in existing_columns:
            continue
        try:
            db.session.execute(
                text(f"ALTER TABLE businesses ADD COLUMN {col_name} {col_def}")
            )
            db.session.commit()
            logger.info("Added missing businesses column: %s", col_name)
        except Exception as exc:
            db.session.rollback()
            logger.warning("Could not add businesses column %s: %s", col_name, exc)


def migrate_users_schema():
    existing_columns = _table_columns("users")
    for col_name, col_def in USER_COLUMNS:
        if col_name in existing_columns:
            continue
        try:
            db.session.execute(
                text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
            )
            db.session.commit()
            logger.info("Added missing users column: %s", col_name)
        except Exception as exc:
            db.session.rollback()
            logger.warning("Could not add users column %s: %s", col_name, exc)

    if "password_hash" in existing_columns:
        try:
            db.session.execute(
                text("ALTER TABLE users MODIFY COLUMN password_hash VARCHAR(255) NULL")
            )
            db.session.commit()
            logger.info("Made users.password_hash nullable")
        except Exception as exc:
            db.session.rollback()
            logger.warning("Could not modify password_hash: %s", exc)


def bootstrap_database(app, seed=True):
    ensure_database_exists()

    with app.app_context():
        db.create_all()
        migrate_scraping_tasks_schema()
        migrate_businesses_schema()
        migrate_users_schema()
        if seed:
            seed_default_admin()

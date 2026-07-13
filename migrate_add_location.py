"""Add location hierarchy and map coordinate columns to scraping_tasks."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db
from sqlalchemy import text

COLUMNS = [
    ("country", "VARCHAR(100) DEFAULT 'Indonesia'"),
    ("province", "VARCHAR(100)"),
    ("regency", "VARCHAR(100)"),
    ("district", "VARCHAR(100)"),
    ("center_lat", "DOUBLE"),
    ("center_lng", "DOUBLE"),
]


def migrate():
    app = create_app()
    with app.app_context():
        for col_name, col_def in COLUMNS:
            try:
                sql = text(f"ALTER TABLE scraping_tasks ADD COLUMN {col_name} {col_def}")
                db.session.execute(sql)
                db.session.commit()
                print(f"  [+] Added column: {col_name}")
            except Exception as e:
                if "Duplicate column" in str(e):
                    print(f"  [=] Column already exists: {col_name}")
                else:
                    print(f"  [!] Error adding {col_name}: {e}")
        print("Migration complete.")


if __name__ == "__main__":
    migrate()

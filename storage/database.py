import pymysql
from datetime import datetime

from config.settings import DB_CONFIG
from utils.logger import get_logger

logger = get_logger("database")


class Database:
    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        try:
            self.connection = pymysql.connect(
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                database=DB_CONFIG["database"],
                charset=DB_CONFIG["charset"],
                autocommit=True,
            )
            logger.info("Database connected")
        except pymysql.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def ensure_connection(self):
        try:
            self.connection.ping(reconnect=True)
        except Exception:
            self.connect()

    def save_business(self, data: dict) -> bool:
        self.ensure_connection()
        try:
            with self.connection.cursor() as cursor:
                sql = """
                    INSERT INTO businesses (
                        name, category, subcategory, address, city, district,
                        regency, province, postal_code, phone, website, email,
                        rating, review_count, google_maps_url, place_id,
                        latitude, longitude, operating_hours,
                        source_keyword, source_location, is_verified
                    ) VALUES (
                        %(name)s, %(category)s, %(subcategory)s, %(address)s, %(city)s, %(district)s,
                        %(regency)s, %(province)s, %(postal_code)s, %(phone)s, %(website)s, %(email)s,
                        %(rating)s, %(review_count)s, %(google_maps_url)s, %(place_id)s,
                        %(latitude)s, %(longitude)s, %(operating_hours)s,
                        %(source_keyword)s, %(source_location)s, %(is_verified)s
                    )
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        category = COALESCE(VALUES(category), category),
                        address = COALESCE(VALUES(address), address),
                        phone = COALESCE(VALUES(phone), phone),
                        website = COALESCE(VALUES(website), website),
                        rating = COALESCE(VALUES(rating), rating),
                        review_count = COALESCE(VALUES(review_count), review_count),
                        updated_at = NOW()
                """
                params = {
                    "name": data.get("name", ""),
                    "category": data.get("category", ""),
                    "subcategory": data.get("subcategory", ""),
                    "address": data.get("address", ""),
                    "city": data.get("city", ""),
                    "district": data.get("district", ""),
                    "regency": data.get("regency", ""),
                    "province": data.get("province", ""),
                    "postal_code": data.get("postal_code", ""),
                    "phone": data.get("phone", ""),
                    "website": data.get("website", ""),
                    "email": data.get("email", ""),
                    "rating": data.get("rating", 0.0),
                    "review_count": data.get("review_count", 0),
                    "google_maps_url": data.get("google_maps_url", ""),
                    "place_id": data.get("place_id", ""),
                    "latitude": data.get("latitude"),
                    "longitude": data.get("longitude"),
                    "operating_hours": data.get("operating_hours", ""),
                    "source_keyword": data.get("source_keyword", ""),
                    "source_location": data.get("source_location", ""),
                    "is_verified": data.get("is_verified", False),
                }
                cursor.execute(sql, params)
                return True
        except pymysql.Error as e:
            logger.error(f"Save business failed: {e}")
            return False

    def create_task(self, keyword: str, location: str) -> int:
        self.ensure_connection()
        try:
            with self.connection.cursor() as cursor:
                sql = """
                    INSERT INTO search_tasks (keyword, location, status)
                    VALUES (%s, %s, 'running')
                """
                cursor.execute(sql, (keyword, location))
                self.connection.commit()
                return cursor.lastrowid
        except pymysql.Error as e:
            logger.error(f"Create task failed: {e}")
            return -1

    def update_task_status(self, task_id: int, status: str, **kwargs):
        self.ensure_connection()
        try:
            with self.connection.cursor() as cursor:
                fields = []
                values = []
                for key, val in kwargs.items():
                    fields.append(f"{key} = %s")
                    values.append(val)

                if status == "running":
                    fields.append("started_at = NOW()")
                elif status in ("completed", "failed"):
                    fields.append("completed_at = NOW()")

                fields.append("status = %s")
                values.append(status)
                values.append(task_id)

                sql = f"UPDATE search_tasks SET {', '.join(fields)} WHERE id = %s"
                cursor.execute(sql, values)
                self.connection.commit()
        except pymysql.Error as e:
            logger.error(f"Update task status failed: {e}")

    def log(self, task_id: int, action: str, message: str, level: str = "INFO"):
        self.ensure_connection()
        try:
            with self.connection.cursor() as cursor:
                sql = """
                    INSERT INTO scraping_logs (task_id, action, message, level)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (task_id, action, message, level))
                self.connection.commit()
        except pymysql.Error as e:
            logger.error(f"Log insert failed: {e}")

    def get_all_businesses(self) -> list:
        self.ensure_connection()
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("SELECT * FROM businesses ORDER BY scraped_at DESC")
                return cursor.fetchall()
        except pymysql.Error as e:
            logger.error(f"Get businesses failed: {e}")
            return []

    def get_business_count(self) -> int:
        self.ensure_connection()
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM businesses")
                return cursor.fetchone()[0]
        except pymysql.Error as e:
            logger.error(f"Count failed: {e}")
            return 0

    def close(self):
        if self.connection:
            try:
                self.connection.close()
                logger.info("Database connection closed")
            except Exception:
                pass
            finally:
                self.connection = None

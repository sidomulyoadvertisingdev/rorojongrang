import csv
import json
from pathlib import Path

from storage.database import Database
from config.settings import DATA_DIR
from utils.logger import get_logger

logger = get_logger("exporter")


class Exporter:
    def __init__(self, db: Database = None):
        self.db = db or Database()

    def to_csv(self, filename: str = None) -> str:
        businesses = self.db.get_all_businesses()
        if not businesses:
            logger.warning("No data to export")
            return ""

        if not filename:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gmaps_data_{timestamp}.csv"

        filepath = DATA_DIR / filename

        headers = [
            "name", "category", "subcategory", "address", "city", "district",
            "regency", "province", "postal_code", "phone", "website", "email",
            "rating", "review_count", "google_maps_url", "latitude", "longitude",
            "operating_hours", "source_keyword", "source_location", "scraped_at"
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            for b in businesses:
                writer.writerow(b)

        logger.info(f"Exported {len(businesses)} records to {filepath}")
        return str(filepath)

    def to_json(self, filename: str = None) -> str:
        businesses = self.db.get_all_businesses()
        if not businesses:
            logger.warning("No data to export")
            return ""

        if not filename:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gmaps_data_{timestamp}.json"

        filepath = DATA_DIR / filename

        for b in businesses:
            for k, v in b.items():
                if hasattr(v, "isoformat"):
                    b[k] = v.isoformat()

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(businesses, f, ensure_ascii=False, indent=2)

        logger.info(f"Exported {len(businesses)} records to {filepath}")
        return str(filepath)

    def export(self, format_type: str = "csv", filename: str = None) -> str:
        if format_type == "json":
            return self.to_json(filename)
        return self.to_csv(filename)

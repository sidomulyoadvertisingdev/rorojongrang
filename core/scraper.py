import json
import time
from datetime import datetime

from core.browser import BrowserManager
from core.navigator import MapNavigator
from core.parser import MapParser
from storage.database import Database
from utils.rate_limiter import RateLimiter
from utils.helpers import build_search_url
from utils.logger import get_logger
from config.settings import SCRAPE_CONFIG

logger = get_logger("scraper")


class GoogleMapsScraper:
    def __init__(self):
        self.browser = BrowserManager()
        self.parser = MapParser()
        self.db = Database()
        self.rate_limiter = RateLimiter()
        self.navigator = None
        self.total_scraped = 0

    def start(self):
        self.browser.create_driver()
        self.navigator = MapNavigator(self.browser.driver, self.rate_limiter)
        logger.info("Scraper started")

    def stop(self):
        self.browser.quit()
        self.db.close()
        logger.info(f"Scraper stopped. Total scraped: {self.total_scraped}")

    def scrape_keyword(self, keyword: str, location: str, category: str = ""):
        logger.info(f"=== Scraping: {keyword} | {location} ===")

        task_id = self.db.create_task(keyword, location)
        search_url = None

        try:
            url = build_search_url(keyword, location)
            self.navigator.handle_consent_dialog()

            if not self.navigator.open_search(url):
                self.db.update_task_status(task_id, "failed", error="Failed to open URL")
                return

            if not self.navigator.wait_for_results():
                self.db.update_task_status(task_id, "failed", error="No results found")
                return

            total_results = self.navigator.scroll_results_panel()

            links = self.navigator.get_result_links()
            if not links:
                self.db.update_task_status(task_id, "failed", error="No links found")
                return

            self.db.update_task_status(task_id, "running", total_results=len(links))

            scraped_count = 0
            for idx, link in enumerate(links):
                try:
                    logger.info(f"[{idx+1}/{len(links)}] Opening: {link[:80]}...")

                    if not self.navigator.open_place(link):
                        continue

                    detail = self.parser.parse_business_detail(self.browser.driver)

                    detail["source_keyword"] = keyword
                    detail["source_location"] = location
                    if category:
                        detail["category"] = category

                    if detail.get("name"):
                        saved = self.db.save_business(detail)
                        if saved:
                            scraped_count += 1
                            self.total_scraped += 1
                            phone = detail.get('phone', 'N/A') or 'N/A'
                            addr = (detail.get('address', 'N/A') or 'N/A')[:50]
                            logger.info(
                                f"  SAVED [{scraped_count}]: {detail['name']} | {phone} | {addr}"
                            )

                    self.rate_limiter.wait()

                except Exception as e:
                    logger.error(f"  Error scraping #{idx+1}: {e}")
                    continue

            self.db.update_task_status(
                task_id, "completed", scraped_results=scraped_count
            )
            logger.info(f"Task completed: {scraped_count}/{len(links)} results scraped")

        except Exception as e:
            logger.error(f"Task failed: {e}")
            self.db.update_task_status(task_id, "failed", error=str(e))

        finally:
            self.browser.restart_if_needed()

    def scrape_from_config(self, config_path: str = None):
        from config.settings import CATEGORIES_FILE

        path = config_path or CATEGORIES_FILE
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)

        categories = config.get("categories", [])
        locations = config.get("locations", [])

        for location in locations:
            for cat in categories:
                for keyword in cat["keywords"]:
                    self.scrape_keyword(keyword, location, cat["name"])

    def scrape_custom(self, keywords: list, locations: list, category: str = ""):
        for location in locations:
            for keyword in keywords:
                self.scrape_keyword(keyword, location, category)

import time
import random

from config.settings import SCRAPE_CONFIG
from utils.logger import get_logger

logger = get_logger("rate_limiter")


class RateLimiter:
    def __init__(self, min_delay: int = None, max_delay: int = None):
        self.min_delay = min_delay or SCRAPE_CONFIG["delay_min"]
        self.max_delay = max_delay or SCRAPE_CONFIG["delay_max"]
        self.request_count = 0

    def wait(self):
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.debug(f"Waiting {delay:.1f}s before next action...")
        time.sleep(delay)
        self.request_count += 1

    def wait_short(self):
        delay = random.uniform(1, 3)
        time.sleep(delay)

    def wait_long(self):
        delay = random.uniform(10, 30)
        logger.debug(f"Long wait {delay:.1f}s...")
        time.sleep(delay)

    def reset(self):
        self.request_count = 0
